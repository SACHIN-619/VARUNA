"""
Round-3 tests: live public-data path (mocked HTTP), stage trace + lineage, notifications,
hash-chained audit trail, permissions / separation of duties, verify-run.
No network is used: live_sources.HTTP_GET is replaced by a deterministic fake that returns
Open-Meteo-shaped JSON.
"""
import random
from datetime import date, datetime, timedelta, timezone

import pytest

from app.services import live_sources as ls

REGION = "IN_KERALA_WAYANAD"
PW = "varuna2026"


def _token(client, email):
    r = client.post("/api/auth/login", data={"username": email, "password": PW})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class FakeOpenMeteo:
    """Deterministic stand-in for the three Open-Meteo endpoints."""

    def __init__(self):
        self.calls = []
        self.forecast_scale = 1.0
        rng = random.Random(7)
        self.truth = {}
        d0 = date.today() - timedelta(days=400)
        for i in range(400):
            d = (d0 + timedelta(days=i)).isoformat()
            self.truth[d] = round(max(0.0, rng.gauss(12, 10)), 1)
        self.bias = {"ncep_gfs_seamless": 6.0, "ecmwf_ifs025": 1.0, "ecmwf_aifs025_single": -2.0,
                     "ukmo_global_deterministic_10km": 3.0, "dwd_icon_global": 4.0}
        self.rng = rng

    def __call__(self, url, params):
        self.calls.append((url, dict(params)))
        models = params.get("models", "").split(",")
        if "archive" in url:
            s, e = date.fromisoformat(params["start_date"]), date.fromisoformat(params["end_date"])
            days = [(s + timedelta(days=i)).isoformat() for i in range((e - s).days + 1)]
            return {"daily": {"time": days, "precipitation_sum": [self.truth.get(d) for d in days]}}, url, b"era5"
        if "previous-runs" in url:
            s, e = date.fromisoformat(params["start_date"]), date.fromisoformat(params["end_date"])
            times, hourly = [], {}
            for i in range((e - s).days + 1):
                d = (s + timedelta(days=i)).isoformat()
                for h in range(24):
                    times.append(f"{d}T{h:02d}:00")
            hourly["time"] = times
            for hv in params["hourly"].split(","):
                n = int(hv[-1])
                for m in models:
                    vals = []
                    for t in times:
                        day_total = max(0.0, self.truth.get(t[:10], 0.0) + self.bias[m] * n / 2)
                        vals.append(round(day_total / 24.0, 3))
                    hourly[f"{hv}_{m}"] = vals
            return {"hourly": hourly}, url, b"prev"
        # forecast
        days = [(date.today() + timedelta(days=i)).isoformat() for i in range(int(params["forecast_days"]))]
        daily = {"time": days}
        for m in models:
            base = 20.0 + self.bias[m]
            daily[f"precipitation_sum_{m}"] = [round(base * self.forecast_scale + i, 1) for i in range(len(days))]
        return {"latitude": 11.7, "longitude": 76.1, "elevation": 800, "daily": daily}, url, repr(daily).encode()


@pytest.fixture
def fake_om(monkeypatch, db_session):
    # isolate from earlier runs (the test DB file persists between sessions)
    from app.models.canonical_record import CanonicalWeatherEntity
    from app.models.notification import ForecastSnapshot
    db_session.query(CanonicalWeatherEntity).filter(CanonicalWeatherEntity.region_id == REGION,
                                                    CanonicalWeatherEntity.provenance == "PUBLIC_API_FORECAST").delete()
    db_session.query(ForecastSnapshot).filter(ForecastSnapshot.region_id == REGION).delete()
    db_session.commit()
    fake = FakeOpenMeteo()
    from app.services import india_sources as ind

    def _no_imd(url, data):
        raise ind.IndiaSourceError("imdpune not reachable in tests")
    monkeypatch.setattr(ind, "IMD_HTTP_POST", _no_imd)
    import tempfile
    monkeypatch.setattr(ind.settings, "DATA_STORAGE_PATH", tempfile.mkdtemp(prefix="varuna_imd_"))
    monkeypatch.setattr(ls, "HTTP_GET", fake)
    monkeypatch.setattr(ls.settings, "AIR_GAPPED_MODE", False)
    monkeypatch.setattr(ls.settings, "LIVE_DATA_ENABLED", True)
    return fake


# ------------------------------------------------------------------------------------------ parsing
def test_series_parser_handles_suffixed_and_plain_keys():
    block = {"precipitation_sum_ecmwf_ifs025": [1, 2], "precipitation_sum": [9, 9]}
    assert ls._series(block, "precipitation_sum", "ecmwf_ifs025", 2) == [1, 2]
    assert ls._series({"precipitation_sum": [3]}, "precipitation_sum", "x", 1) == [3]
    assert ls._series({"precipitation_sum": [3]}, "precipitation_sum", "x", 2) is None


def test_hourly_aggregation_requires_full_day():
    times = [f"2026-01-01T{h:02d}:00" for h in range(24)] + [f"2026-01-02T{h:02d}:00" for h in range(5)]
    vals = [1.0] * 29
    out = ls._aggregate_hourly(times, vals, "sum")
    assert out["2026-01-01"] == 24.0 and out["2026-01-02"] is None


def test_restricted_models_are_refused():
    with pytest.raises(ls.LiveSourceError):
        ls._om_ids(["NCUM"])


def test_air_gapped_blocks_live(monkeypatch):
    monkeypatch.setattr(ls.settings, "AIR_GAPPED_MODE", True)
    with pytest.raises(ls.LiveSourceError):
        ls.fetch_forecast({"lat": 1, "lon": 1, "region_id": "X", "name": "X"}, "rainfall", ["GFS"])


# ------------------------------------------------------------------------------------- permissions
def test_forecaster_cannot_fetch_or_ingest(client):
    h = _token(client, "forecaster@ncmrwf.gov.in")
    assert client.post("/api/live/fetch", json={"region_id": REGION}, headers=h).status_code == 403
    r = client.post("/api/datasets/ingest", files={"file": ("x.csv", b"a,b\n1,2\n")}, headers=h)
    assert r.status_code == 403 and "data:ingest" in r.json()["detail"]
    assert client.get("/api/live/sources", headers=h).status_code == 200


def test_roles_matrix_and_me(client):
    m = client.get("/api/auth/roles").json()["matrix"]
    assert "live:fetch" in m["OPERATIONS"] and "live:fetch" not in m["FORECASTER"]
    assert "change:approve" in m["ADMIN"] and "change:propose" not in m["ADMIN"]
    assert "audit:view" in m["AUDITOR"] and "data:ingest" not in m["AUDITOR"]
    me = client.get("/api/auth/me", headers=_token(client, "ops@ncmrwf.gov.in")).json()
    assert "live:fetch" in me["permissions"]


def test_no_public_registration_and_admin_creates_users(client):
    assert client.post("/api/auth/register", json={"email": "x@y.z"}).status_code in (404, 405)
    h = _token(client, "admin@ncmrwf.gov.in")
    email = f"new.{datetime.now().timestamp():.0f}@ncmrwf.gov.in"
    r = client.post("/api/auth/users", json={"name": "New Forecaster", "email": email, "role": "FORECASTER",
                                             "region_scope": [REGION], "reason": "test onboarding"}, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["initial_password"] and r.json()["region_scope"] == [REGION]
    fh = _token(client, "forecaster@ncmrwf.gov.in")
    assert client.get("/api/auth/users", headers=fh).status_code == 403


# ---------------------------------------------------------------------------------- live data path
def test_live_fetch_stores_traceable_records_and_dashboard_uses_them(client, fake_om):
    h = _token(client, "ops@ncmrwf.gov.in")
    r = client.post("/api/live/fetch", json={"region_id": REGION, "variables": ["rainfall"]}, headers=h)
    assert r.status_code == 200, r.text
    res = r.json()["results"][0]
    assert set(res["models_received"]) == set(ls.DEFAULT_LIVE_MODELS)
    assert res["records"] == 5 * 4 and len(res["checksum"]) == 64

    s = client.get("/api/dashboard/summary", params={"region_id": REGION, "variable": "rainfall", "lead_hours": 48,
                                                     "strategy": "ADAPTIVE_RELIABILITY"}).json()
    assert s["source_mode"] == "LIVE_PUBLIC_MODELS"
    assert set(s["models"]) == set(ls.DEFAULT_LIVE_MODELS)
    # lead 48 = day index 1 -> base + bias + 1
    assert s["model_forecasts"]["GFS"] == pytest.approx(20.0 + 6.0 + 1)
    assert s["source_meta"]["ECMWF_IFS"]["source"] == "OPEN_METEO:ecmwf_ifs025"
    assert s["source_meta"]["ECMWF_IFS"]["provenance"] == "PUBLIC_API_FORECAST"
    # stage trace: 14 stages, verification pending (future valid time)
    keys = [t["key"] for t in s["stage_trace"]]
    assert len(keys) == 14 and keys[0] == "INGEST" and keys[-1] == "VERIFY"
    assert s["stage_trace"][-1]["status"] == "PENDING"
    # lineage: fused value reproducible from its terms
    lin = s["lineage"]["fused_value"]
    assert lin["value"] == s["fused_value"]
    total = sum(t["weight"] * t["value"] for t in lin["terms"] if t["value"] is not None)
    assert total == pytest.approx(s["fused_value"], abs=0.15)
    # weights simplex
    assert sum(w["weight"] for w in s["weights"]) == pytest.approx(1.0, abs=1e-3)
    # NCUM/WRF are not silently invented
    assert "NCUM" not in s["model_forecasts"] and "WRF" not in s["model_forecasts"]


def test_demo_source_is_labelled_synthetic(client):
    s = client.get("/api/dashboard/summary", params={"source": "demo"}).json()
    assert s["source_mode"] == "SYNTHETIC_DEMO"
    assert len(s["stage_trace"]) == 14


def test_backfill_builds_verified_skill_and_fits_stacker(client, fake_om, db_session):
    h = _token(client, "ops@ncmrwf.gov.in")
    r = client.post("/api/live/backfill", json={"region_id": REGION, "variable": "rainfall", "days": 40}, headers=h)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["verification_rows"] == 40 * 5 * 2 and rep["observations"] == 40
    card = rep["leads"]["24"]
    # GFS has +6 mm/2 wet bias at lead 24 -> MAE 3.0
    assert card["per_model"]["GFS"]["BIAS"] == pytest.approx(3.0, abs=0.05)
    assert card["holdout"]["stacking_mae"] <= card["holdout"]["simple_average_mae"] + 1e-6
    assert "fitted" in card["stacker"]

    from app.models.skill import ModelSkill
    row = db_session.query(ModelSkill).filter(ModelSkill.model_id == "GFS", ModelSkill.region_id == REGION,
                                              ModelSkill.lead_hours == 48, ModelSkill.metric == "MAE",
                                              ModelSkill.evaluation_period == ls.BACKFILL_PERIOD).first()
    assert row is not None and row.sample_count == 40 and row.value == pytest.approx(6.0, abs=0.05)

    # pipeline now uses verified history + the fitted stacker for this model set
    client.post("/api/live/fetch", json={"region_id": REGION}, headers=h)
    s = client.get("/api/dashboard/summary", params={"region_id": REGION, "lead_hours": 48,
                                                     "strategy": "BIAS_CORRECTED_STACK"}).json()
    assert s["strategy"] == "BIAS_CORRECTED_STACK", s.get("strategy_note")
    assert set(s["skill_provenance"].values()) == {"DATABASE_VERIFIED_HISTORY"}
    trust = next(t for t in s["stage_trace"] if t["key"] == "TRUST")
    assert trust["status"] == "PASS"
    # bias-corrected GFS value (26 - 6) should dominate the fused value -> close to 20-21
    assert 17.0 <= s["fused_value"] <= 23.0


def test_sudden_change_creates_traceable_notification(client, fake_om):
    h = _token(client, "ops@ncmrwf.gov.in")
    params = {"region_id": REGION, "lead_hours": 24, "strategy": "ADAPTIVE_RELIABILITY"}
    client.post("/api/live/fetch", json={"region_id": REGION}, headers=h)
    client.get("/api/dashboard/summary", params=params)
    fh = _token(client, "forecaster@ncmrwf.gov.in")
    before = client.get("/api/notifications", headers=fh).json()
    # next issue: models triple their rainfall
    fake_om.forecast_scale = 3.0
    import app.services.live_sources as mod
    real_now = datetime.now(timezone.utc)

    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return real_now + timedelta(hours=1)
    mod.datetime = _DT
    try:
        client.post("/api/live/fetch", json={"region_id": REGION}, headers=h)
    finally:
        mod.datetime = datetime
    s = client.get("/api/dashboard/summary", params=params).json()
    assert s["notification_id"], "a large jump must notify"
    n = client.get(f"/api/notifications/{s['notification_id']}", headers=fh).json()
    r1 = next(r for r in n["math"]["rules"] if r["rule"] == "R1_FUSED_JUMP")
    assert r1["triggered"] and r1["values"]["F_now"] > r1["values"]["F_prev"]
    assert n["sources"]["current"][0]["received_at"] and n["sources"]["current"][0]["source"].startswith("OPEN_METEO:")
    after = client.get("/api/notifications", headers=fh).json()
    assert after["unread"] >= before["unread"] + 1
    assert client.post(f"/api/notifications/{n['id']}/read", headers=fh).status_code == 200
    # identical inputs -> no duplicate snapshot / notification
    s2 = client.get("/api/dashboard/summary", params=params).json()
    assert s2["notification_id"] is None


def test_verify_run_manual_observation(client):
    h = _token(client, "forecaster@ncmrwf.gov.in")
    r = client.post("/api/verification/verify-run", json={"source": "demo", "observed_value": 70.0,
                                                          "observation_source": "TEST_GAUGE_42"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "VERIFIED" and body["observation_source"] == "TEST_GAUGE_42"
    assert "VARUNA_FUSED" in body["forecast_errors"]
    # ERA5 for a future date is honestly "awaiting"
    r = client.post("/api/verification/verify-run", json={"source": "demo", "use_era5": True}, headers=h)
    assert r.json()["status"] == "AWAITING_OBSERVATION"


# ------------------------------------------------------------------------------ audit + governance
def test_audit_chain_is_intact_and_detects_tampering(client, db_session):
    h = _token(client, "auditor@ncmrwf.gov.in")
    v = client.get("/api/audit/verify-chain", headers=h).json()
    assert v["intact"] is True and v["checked"] > 0
    ev = client.get("/api/audit/events", params={"action": "LOGIN"}, headers=h).json()
    assert ev["total"] > 0
    assert client.get("/api/audit/events", headers=_token(client, "forecaster@ncmrwf.gov.in")).status_code == 403

    from app.models.audit import AuditLog
    row = db_session.query(AuditLog).filter(AuditLog.seq.isnot(None)).order_by(AuditLog.seq.desc()).first()
    with pytest.raises(PermissionError):
        row.reason = "edited"
        db_session.commit()
    db_session.rollback()
    # raw SQL bypassing the ORM guard is detected by the hash chain
    from sqlalchemy import text
    original = row.result
    db_session.execute(text("UPDATE audit_logs SET result='TAMPERED' WHERE seq=:s"), {"s": row.seq})
    db_session.commit()
    from app.services.audit_service import verify_chain
    broken = verify_chain(db_session)
    assert broken["intact"] is False and broken["broken_at_seq"] == row.seq
    db_session.execute(text("UPDATE audit_logs SET result=:r WHERE seq=:s"), {"r": original, "s": row.seq})
    db_session.commit()
    assert verify_chain(db_session)["intact"] is True


def test_propose_approve_separation_of_duties(client):
    ah = _token(client, "analyst@ncmrwf.gov.in")
    adm = _token(client, "admin@ncmrwf.gov.in")
    # admins cannot propose scientific changes, analysts cannot approve
    assert client.post("/api/governance/proposals", json={"change_type": "SET_DEFAULT_STRATEGY",
                       "payload": {"strategy": "ADAPTIVE_RELIABILITY"}, "justification": "admin tries it"},
                       headers=adm).status_code == 403
    p = client.post("/api/governance/proposals", json={"change_type": "SET_DEFAULT_STRATEGY",
                    "payload": {"strategy": "ADAPTIVE_RELIABILITY"},
                    "justification": "Reliability weights beat ML on the live backfill"}, headers=ah)
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    assert client.post(f"/api/governance/proposals/{pid}/approve", json={"reason": "self"}, headers=ah).status_code == 403
    r = client.post(f"/api/governance/proposals/{pid}/approve", json={"reason": "reviewed evidence"}, headers=adm)
    assert r.status_code == 200 and r.json()["status"] == "APPLIED"
    assert client.get("/api/governance/config", headers=adm).json()["config"]["default_strategy"] == "ADAPTIVE_RELIABILITY"
    s = client.get("/api/dashboard/summary", params={"source": "demo"}).json()
    assert s["strategy"] == "ADAPTIVE_RELIABILITY"
    # restore default via the same process
    p2 = client.post("/api/governance/proposals", json={"change_type": "SET_DEFAULT_STRATEGY",
                     "payload": {"strategy": "ADAPTIVE_ML"}, "justification": "restore default after test"}, headers=ah).json()
    client.post(f"/api/governance/proposals/{p2['id']}/approve", json={"reason": "restore"}, headers=adm)


def test_qc_states_quarantine_stale_and_reject_unphysical():
    from app.services.canonical_pipeline import canonical_pipeline
    old = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    pkg = canonical_pipeline.execute_pipeline(
        db=None, region_id="IN_TELANGANA_DECCAN", variable="temperature", lead_hours=24,
        raw_forecasts={"GFS": 35.0, "ECMWF_IFS": 99.0, "ICON": 34.0, "UKMO_UM": None, "AI_WEATHER": 36.0},
        source_meta={"AI_WEATHER": {"issue_time": old, "source": "OPEN_METEO:x", "provenance": "PUBLIC_API_FORECAST"}},
        strategy="ADAPTIVE_RELIABILITY")
    st = pkg["inputs"]["qc_state"]
    assert st == {"GFS": "ACCEPTED", "ECMWF_IFS": "REJECTED", "ICON": "ACCEPTED", "UKMO_UM": "MISSING",
                  "AI_WEATHER": "QUARANTINED"}
    w = pkg["trust_modeling"]["final_weights"]
    assert w.get("ECMWF_IFS", 0) == 0 and w.get("AI_WEATHER", 0) == 0
    assert 34.0 <= pkg["fusion"]["fused_value"] <= 35.0
