"""India-first sources: IMD gridded parser/truth, backfill against IMD, IMD API adapter, NCMRWF drop, merged feed."""
import os
import tempfile
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pytest

from app.services import india_sources as ind
from app.services import live_sources as ls
from tests.test_live_trace_governance import FakeOpenMeteo, _token

REGION = "IN_TELANGANA_DECCAN"   # centroid 17.385 N, 78.4867 E
SP = ind.GRID_SPECS["rain"]
LATS = np.linspace(SP["lat0"], SP["lat1"], SP["nlat"])
LONS = np.linspace(SP["lon0"], SP["lon1"], SP["nlon"])


def rain_grid(value_fn, days=1):
    g = np.full((days, SP["nlat"], SP["nlon"]), -999.0, dtype="<f4")
    i = int(np.abs(LATS - 17.385).argmin()); j = int(np.abs(LONS - 78.4867).argmin())
    for d in range(days):
        g[d, i - 3:i + 4, j - 3:j + 4] = value_fn(d)
    return g.tobytes(), i, j


class FakeIMD:
    """Stand-in for imdpune.gov.in: real-time daily rain = truth of FakeOpenMeteo for that day."""
    def __init__(self, truth):
        self.truth, self.calls = truth, []

    def __call__(self, url, data):
        self.calls.append((url, data))
        key = list(data.values())[0]
        d = datetime.strptime(str(key), "%d%m%Y").date()
        raw, _, _ = rain_grid(lambda _: self.truth.get(d.isoformat(), 0.0))
        return raw


@pytest.fixture
def imd_env(monkeypatch):
    monkeypatch.setattr(ind.settings, "DATA_STORAGE_PATH", tempfile.mkdtemp(prefix="varuna_imd_"))
    monkeypatch.setattr(ind.settings, "AIR_GAPPED_MODE", False)
    monkeypatch.setattr(ls.settings, "LIVE_DATA_ENABLED", True)
    om = FakeOpenMeteo()
    monkeypatch.setattr(ls, "HTTP_GET", om)
    fake = FakeIMD(om.truth)
    monkeypatch.setattr(ind, "IMD_HTTP_POST", fake)
    return om, fake


def test_grid_parser_missing_values_and_coastal_search():
    raw, i, j = rain_grid(lambda d: 12.5)
    g = ind.parse_grid(raw, "rainfall", "realtime", 1)
    assert g.shape == (1, 129, 135) and np.isnan(g[0, 0, 0])
    v, cell = ind.grid_point(g[0], "rainfall", "realtime", 17.385, 78.4867)
    assert v == 12.5 and abs(cell["cell_lat"] - 17.5) < 0.2
    # centroid on a missing cell -> nearest valid within 2 cells
    g2 = g.copy(); g2[0, i, j] = np.nan
    v2, cell2 = ind.grid_point(g2[0], "rainfall", "realtime", 17.385, 78.4867)
    assert v2 == 12.5 and (cell2["cell_lat"], cell2["cell_lon"]) != (cell["cell_lat"], cell["cell_lon"])
    with pytest.raises(ind.IndiaSourceError):
        ind.parse_grid(b"\x00" * 1000, "rainfall", "realtime")


def test_imd_truth_realtime_fetch_and_cache(imd_env):
    om, fake = imd_env
    d = date.today() - timedelta(days=3)
    region = {"region_id": REGION, "name": "T", "lat": 17.385, "lon": 78.4867}
    res = ind.fetch_imd_truth(region, "rainfall", d, d)
    assert res["truth"][d.isoformat()] == pytest.approx(om.truth[d.isoformat()], abs=0.01)
    assert fake.calls[0][0].endswith("/Realtimedata/Rainfall/rain.php") and fake.calls[0][1] == {"rain": d.strftime("%d%m%Y")}
    ind.fetch_imd_truth(region, "rainfall", d, d)
    assert len(fake.calls) == 1, "second call must hit the disk cache"
    with pytest.raises(ind.IndiaSourceError):
        ind.fetch_imd_truth(region, "wind_speed", d, d)


def test_backfill_prefers_imd_truth(client, imd_env, db_session):
    h = _token(client, "ops@ncmrwf.gov.in")
    r = client.post("/api/live/backfill", json={"region_id": REGION, "variable": "rainfall", "days": 30}, headers=h)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["truth"] == "OBS_IMD" and rep["day_window_offset_hours"] == 9
    assert rep["observations"] == 30 and rep["verification_rows"] == 30 * 5 * 2
    from app.models.skill import ModelSkill
    row = db_session.query(ModelSkill).filter(ModelSkill.region_id == REGION, ModelSkill.model_id == "GFS",
                                              ModelSkill.lead_hours == 24, ModelSkill.metric == "MAE").first()
    assert row.evaluation_period == "LIVE_BACKFILL_IMD" and row.sample_count == 30
    sk = client.get("/api/verification/live-skill", params={"region_id": REGION}).json()
    assert "IMD" in sk["reference"]
    # wind has no IMD product -> ERA5 with an explicit note
    rw = client.post("/api/live/backfill", json={"region_id": REGION, "variable": "wind_speed", "days": 15}, headers=h).json()
    assert rw["truth"] == "OBS_ERA5" and "no wind" in rw["truth_note"]


def test_backfill_auto_falls_back_to_era5_when_imd_unreachable(client, imd_env, monkeypatch):
    def down(url, data):
        raise ind.IndiaSourceError("connection refused")
    monkeypatch.setattr(ind, "IMD_HTTP_POST", down)
    h = _token(client, "ops@ncmrwf.gov.in")
    rep = client.post("/api/live/backfill", json={"region_id": REGION, "variable": "rainfall", "days": 12}, headers=h).json()
    assert rep["truth"] == "OBS_ERA5" and "fell back to ERA5" in rep["truth_note"]
    strict = client.post("/api/live/backfill", json={"region_id": REGION, "variable": "rainfall", "days": 12,
                                                     "truth_source": "IMD_GRIDDED"}, headers=h)
    assert strict.status_code == 502


def test_imd_grid_upload_validates_and_caches(client, imd_env):
    h = _token(client, "ops@ncmrwf.gov.in")
    raw, _, _ = rain_grid(lambda d: 7.0)
    day = (date.today() - timedelta(days=40)).isoformat()
    r = client.post("/api/india/imd-grid/upload", data={"variable": "rainfall", "kind": "realtime", "key": day},
                    files={"file": ("rain.grd", raw)}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["days"] == 1
    bad = client.post("/api/india/imd-grid/upload", data={"variable": "rainfall", "kind": "realtime", "key": day},
                      files={"file": ("x.grd", b"\x00" * 100)}, headers=h)
    assert bad.status_code == 422
    fh = _token(client, "forecaster@ncmrwf.gov.in")
    assert client.post("/api/india/imd-grid/upload", data={"variable": "rainfall", "kind": "realtime", "key": day},
                       files={"file": ("rain.grd", raw)}, headers=fh).status_code == 403


def test_imd_api_adapter(monkeypatch, client):
    h = _token(client, "forecaster@ncmrwf.gov.in")
    monkeypatch.setattr(ind.settings, "IMD_API_ENABLED", False)
    assert client.get("/api/india/imd/observation", params={"region_id": REGION}, headers=h).status_code == 503
    monkeypatch.setattr(ind.settings, "IMD_API_ENABLED", True)
    monkeypatch.setattr(ind.settings, "AIR_GAPPED_MODE", False)
    seen = {}

    def fake_get(url, params):
        seen["url"], seen["params"] = url, params
        return [{"Station Id": "43128", "Station": "HYDERABAD", "Date of Observation": "2026-10-03",
                 "Time of Observation": "0300", "Temperature": "24.6", "Wind Speed KMPH": "18",
                 "Last 24 hrs Rainfall": "35.2"}]
    monkeypatch.setattr(ind, "IMD_API_GET", fake_get)
    obs = client.get("/api/india/imd/observation", params={"region_id": REGION}, headers=h).json()
    assert seen["url"].endswith("/current_wx") and seen["params"] == {"id": "43128"}
    assert obs["rainfall_24h_mm"] == 35.2 and obs["wind_speed_ms"] == 5.0 and obs["station"] == "HYDERABAD"


def test_india_catalog_tiers(client):
    h = _token(client, "forecaster@ncmrwf.gov.in")
    cat = client.get("/api/india/sources", headers=h).json()
    assert cat["tiers"][0] == "INDIA_PRIMARY"
    ids = [s["id"] for s in cat["india_primary"]]
    assert ids[:3] == ["IMD_GRIDDED", "IMD_API", "NCMRWF_NCUM"]
    assert "Never labelled" in cat["global_reference"]["note"]


def test_ncmrwf_drop_and_india_first_merge(client, imd_env, monkeypatch, db_session):
    om, _ = imd_env
    folder = tempfile.mkdtemp(prefix="ncmrwf_drop_")
    monkeypatch.setattr(ind.settings, "NCMRWF_DROP_DIR", folder)
    today = datetime.now(timezone.utc).date()
    valid = today + timedelta(days=1)   # lead 48 h bucket of a fetch made today
    with open(os.path.join(folder, "ncum_g_telangana.csv"), "w") as f:
        f.write("cycle_id,issue_date,valid_date,region_id,region_name,season,weather_regime,variable,unit,lead_hours,model_id,forecast_value\n")
        run = datetime.now().strftime("%H%M%S%f")   # unique content per run (the test DB persists)
        f.write(f"{run},{today},{valid},{REGION},Telangana,SW_MONSOON,HEAVY_RAINFALL,rainfall,mm,48,NCUM_G,31.5\n")
        f.write(f"{run},{today},{valid},{REGION},Telangana,SW_MONSOON,HEAVY_RAINFALL,rainfall,mm,48,GFS,40.0\n")
    h = _token(client, "ops@ncmrwf.gov.in")
    r = client.post("/api/india/ncmrwf/scan", headers=h)
    assert r.status_code == 200, r.text
    first = r.json()["files"][0]
    assert first["status"] == "INGESTED", first
    assert client.post("/api/india/ncmrwf/scan", headers=h).json()["files"][0]["status"] == "SKIPPED_DUPLICATE"

    from app.models.canonical_record import CanonicalWeatherEntity
    recs = db_session.query(CanonicalWeatherEntity).filter(CanonicalWeatherEntity.dataset_id == first["dataset_id"]).all()
    assert recs and {r.provenance for r in recs} == {"AUTHORIZED_OPERATIONAL_FEED"}

    client.post("/api/live/fetch", json={"region_id": REGION}, headers=h)   # global models for the same valid day
    s = client.get("/api/dashboard/summary", params={"region_id": REGION, "lead_hours": 48,
                                                     "strategy": "ADAPTIVE_RELIABILITY"}).json()
    assert s["source_mode"] == "INDIA_OPERATIONAL_PLUS_GLOBAL", s["source_mode"]
    assert s["model_forecasts"]["NCUM"] == 31.5
    assert s["model_forecasts"]["GFS"] == 40.0, "authorised Indian GFS file must win over the public API copy"
    assert s["source_meta"]["GFS"]["provenance"] == "AUTHORIZED_OPERATIONAL_FEED"
    assert s["source_meta"]["ECMWF_IFS"]["provenance"] == "PUBLIC_API_FORECAST"
