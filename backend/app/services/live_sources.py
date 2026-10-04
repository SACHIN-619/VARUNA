"""
VARUNA live public-data connector (Open-Meteo).

What this gives the pipeline, honestly labelled:
  * PUBLIC_API_FORECAST  - current global model forecasts (GFS, ECMWF IFS, ECMWF AIFS, UK Met Office UM global,
                           DWD ICON) for a region centroid, daily aggregates, via https://open-meteo.com
  * PUBLIC_API_FORECAST  - *previous runs* of the same models for past days (lead 24 h / 48 h buckets), used to
                           build a verification history
  * REANALYSIS_REFERENCE - ERA5 daily values (~5 day latency) used as the verification "truth"

What it does NOT give:
  * NCUM (NCMRWF) and IMD WRF have no public API. They need institutional access (NCMRWF data portal /
    IMD API registration) and enter VARUNA through file ingestion or a future authorised connector.
  * ERA5 is a reanalysis at ~0.25 deg, not a rain-gauge observation. For station truth use IMD gridded
    rainfall (imdlib) or IMD AWS/ARG data when available.
  * Values are point extractions at the region centroid (nearest grid cell), not area averages.

Licence: the free Open-Meteo API is for non-commercial use (CC BY 4.0 attribution). Set OPEN_METEO_API_KEY
and the customer URLs for commercial deployments.

Network calls go through `HTTP_GET`, which tests replace with a fake. Nothing here runs at import time.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("varuna.live")

# Canonical VARUNA slot -> public model
LIVE_MODELS: Dict[str, Dict[str, str]] = {
    "GFS": {"open_meteo_id": "ncep_gfs_seamless", "name": "NOAA NCEP GFS", "provider": "NOAA (USA)",
            "kind": "NWP_GLOBAL", "resolution": "0.11-0.25 deg"},
    "ECMWF_IFS": {"open_meteo_id": "ecmwf_ifs025", "name": "ECMWF IFS (open data)", "provider": "ECMWF",
                  "kind": "NWP_GLOBAL", "resolution": "0.25 deg"},
    "AI_WEATHER": {"open_meteo_id": "ecmwf_aifs025_single", "name": "ECMWF AIFS (machine-learning model)",
                   "provider": "ECMWF", "kind": "AI_GLOBAL", "resolution": "0.25 deg"},
    "UKMO_UM": {"open_meteo_id": "ukmo_global_deterministic_10km", "name": "UK Met Office Unified Model (global)",
                "provider": "UK Met Office", "kind": "NWP_GLOBAL", "resolution": "10 km",
                "note": "Same model family as NCMRWF's NCUM, but NOT NCUM."},
    "ICON": {"open_meteo_id": "dwd_icon_global", "name": "DWD ICON (global)", "provider": "DWD (Germany)",
             "kind": "NWP_GLOBAL", "resolution": "13 km"},
}
DEFAULT_LIVE_MODELS = ["GFS", "ECMWF_IFS", "AI_WEATHER", "UKMO_UM", "ICON"]

RESTRICTED_SOURCES = {
    "NCUM": "NCMRWF Unified Model - no public API. Request access via NCMRWF (ncmrwf.gov.in data portal / MoES "
            "data-sharing) and ingest the files, or add an authorised connector.",
    "WRF": "IMD WRF - no public API. Obtain via IMD (mausam.imd.gov.in) under an institutional agreement.",
}

# VARUNA variable -> (daily aggregate name, hourly name, aggregation, unit)
VARIABLES: Dict[str, Dict[str, str]] = {
    "rainfall": {"daily": "precipitation_sum", "hourly": "precipitation", "agg": "sum", "unit": "mm"},
    "temperature": {"daily": "temperature_2m_max", "hourly": "temperature_2m", "agg": "max", "unit": "°C"},
    "wind_speed": {"daily": "wind_speed_10m_max", "hourly": "wind_speed_10m", "agg": "max", "unit": "m/s"},
}

LOCAL_TZ = "Asia/Kolkata"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0); model data from NOAA, ECMWF, UK Met Office, DWD; ERA5 from Copernicus/ECMWF."
BACKFILL_PERIOD = "LIVE_BACKFILL_ERA5"          # truth = ERA5 (global fallback)
BACKFILL_PERIOD_IMD = "LIVE_BACKFILL_IMD"       # truth = IMD gridded (preferred for India)
BACKFILL_PERIODS = (BACKFILL_PERIOD_IMD, BACKFILL_PERIOD)
ERA5_LATENCY_DAYS = 6


class LiveSourceError(RuntimeError):
    pass


# --------------------------------------------------------------------------------------------- HTTP
def _default_http_get(url: str, params: Dict[str, Any]) -> Tuple[Dict[str, Any], str, bytes]:
    if settings.OPEN_METEO_API_KEY:
        params = {**params, "apikey": settings.OPEN_METEO_API_KEY}
    full = f"{url}?{urllib.parse.urlencode(params, safe=',')}"
    req = urllib.request.Request(full, headers={"User-Agent": "VARUNA-forecast-intelligence/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=settings.LIVE_HTTP_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
    except Exception as exc:  # network, DNS, proxy, HTTP error
        detail = ""
        if hasattr(exc, "read"):
            try:
                detail = exc.read().decode("utf-8", "ignore")[:300]
            except Exception:
                pass
        raise LiveSourceError(f"Request to {url} failed: {exc} {detail}".strip()) from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise LiveSourceError(f"Non-JSON response from {url}") from exc
    if isinstance(data, dict) and data.get("error"):
        raise LiveSourceError(f"{url}: {data.get('reason', 'provider error')}")
    # never echo the API key back into lineage
    return data, full.replace(settings.OPEN_METEO_API_KEY, "***") if settings.OPEN_METEO_API_KEY else full, raw


HTTP_GET: Callable[[str, Dict[str, Any]], Tuple[Dict[str, Any], str, bytes]] = _default_http_get


def live_enabled() -> Tuple[bool, str]:
    if settings.AIR_GAPPED_MODE:
        return False, "AIR_GAPPED_MODE is on: outbound calls are blocked."
    if not settings.LIVE_DATA_ENABLED:
        return False, "LIVE_DATA_ENABLED=false in backend .env."
    return True, "enabled"


def _require_enabled():
    ok, why = live_enabled()
    if not ok:
        raise LiveSourceError(why)


# ------------------------------------------------------------------------------------------ helpers
def _om_ids(models: Iterable[str]) -> List[str]:
    out = []
    for m in models:
        if m not in LIVE_MODELS:
            raise LiveSourceError(f"Model '{m}' has no public source. {RESTRICTED_SOURCES.get(m, '')}".strip())
        out.append(LIVE_MODELS[m]["open_meteo_id"])
    return out


def _series(block: Dict[str, Any], var: str, om_id: str, n_models: int) -> Optional[List[Any]]:
    """Open-Meteo suffixes variables with the model id when several models are requested."""
    for key in (f"{var}_{om_id}", var if n_models == 1 else None):
        if key and key in block:
            return block[key]
    return None


def _clean(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else round(f, 2)


def resolve_region(db, region_id: str) -> Dict[str, Any]:
    from app.services.harmonization import normalize_region_id
    rid = normalize_region_id(region_id)
    cen = None
    name = rid
    if db is not None:
        from app.models.region import Region
        r = db.query(Region).filter(Region.id == rid).first()
        if r is not None:
            cen, name = r.centroid, r.name
    if not cen:
        from app.db.seed import REGIONS_DATA
        for r in REGIONS_DATA:
            if r["id"] == rid:
                cen, name = r.get("centroid"), r.get("name", rid)
                break
    if not cen or cen.get("lat") is None:
        raise LiveSourceError(f"Region '{region_id}' has no centroid; live extraction needs lat/lon.")
    return {"region_id": rid, "name": name, "lat": float(cen["lat"]), "lon": float(cen["lon"])}


def _rid(*parts) -> str:
    return "LV_" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:32]


def _checksum(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# -------------------------------------------------------------------------------------------- fetch
def fetch_forecast(region: Dict[str, Any], variable: str, models: List[str], days: int = 4) -> Dict[str, Any]:
    """Latest forecast for each model. Day index i (0 = today, local time) -> lead bucket 24*(i+1) h."""
    _require_enabled()
    v = VARIABLES.get(variable)
    if not v:
        raise LiveSourceError(f"Variable '{variable}' is not available from the live source.")
    om = _om_ids(models)
    params = {"latitude": region["lat"], "longitude": region["lon"], "daily": v["daily"],
              "models": ",".join(om), "forecast_days": max(1, min(days, 10)), "timezone": LOCAL_TZ,
              "wind_speed_unit": "ms", "precipitation_unit": "mm", "temperature_unit": "celsius"}
    fetched_at = datetime.now(timezone.utc)
    data, url, raw = HTTP_GET(settings.OPEN_METEO_FORECAST_URL, params)
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    series: Dict[str, List[Dict[str, Any]]] = {}
    missing: Dict[str, str] = {}
    for slot, om_id in zip(models, om):
        vals = _series(daily, v["daily"], om_id, len(om))
        if vals is None:
            missing[slot] = "variable not returned for this model"
            continue
        pts = [{"date": d, "lead_hours": 24 * (i + 1), "value": _clean(x)} for i, (d, x) in enumerate(zip(dates, vals))]
        if all(p["value"] is None for p in pts):
            missing[slot] = "model returned only nulls (not available for this location / variable)"
            continue
        series[slot] = pts
    return {
        "kind": "FORECAST", "region": region, "variable": variable, "unit": v["unit"], "aggregate": v["daily"],
        "fetched_at": fetched_at.isoformat(), "url": url, "checksum": _checksum(raw),
        "grid": {"latitude": data.get("latitude"), "longitude": data.get("longitude"), "elevation": data.get("elevation")},
        "series": series, "missing": missing,
        "note": "Open-Meteo serves the latest available run of each model; the exact model cycle time is not "
                "exposed by this endpoint. Day 0 = today (Asia/Kolkata) and is treated as the 24 h lead bucket.",
    }


def _aggregate_hourly(times: List[str], vals: List[Any], how: str, offset_hours: int = 0) -> Dict[str, Optional[float]]:
    """
    Hourly values -> daily. offset_hours shifts the day window: with 9 the day D covers hours stamped
    09:00 D .. 08:00 D+1 local (≈ the IMD 08:30 IST rainfall day); 0 = calendar day.
    """
    by_day: Dict[str, List[float]] = defaultdict(list)
    counts: Dict[str, int] = defaultdict(int)
    for t, x in zip(times, vals):
        if offset_hours:
            try:
                d = (datetime.fromisoformat(str(t)) - timedelta(hours=offset_hours)).date().isoformat()
            except ValueError:
                continue
        else:
            d = str(t)[:10]
        counts[d] += 1
        c = _clean(x)
        if c is not None:
            by_day[d].append(c)
    out: Dict[str, Optional[float]] = {}
    for d, n in counts.items():
        xs = by_day.get(d, [])
        if len(xs) < 20:  # require (nearly) a full local day
            out[d] = None
        else:
            out[d] = round(sum(xs) if how == "sum" else max(xs), 2)
    return out


def fetch_previous_runs(region: Dict[str, Any], variable: str, models: List[str], start: date, end: date,
                        lead_days: Iterable[int] = (1, 2), offset_hours: int = 0) -> Dict[str, Any]:
    """Forecasts issued N days before each valid day (Open-Meteo previous-runs API), aggregated to local days."""
    _require_enabled()
    v = VARIABLES[variable]
    om = _om_ids(models)
    lead_days = [int(n) for n in lead_days if 1 <= int(n) <= 7]
    hourly_vars = [f"{v['hourly']}_previous_day{n}" for n in lead_days]
    params = {"latitude": region["lat"], "longitude": region["lon"], "hourly": ",".join(hourly_vars),
              "models": ",".join(om), "start_date": start.isoformat(),
              "end_date": (end + timedelta(days=1 if offset_hours else 0)).isoformat(),
              "timezone": LOCAL_TZ, "wind_speed_unit": "ms", "precipitation_unit": "mm"}
    data, url, raw = HTTP_GET(settings.OPEN_METEO_PREVIOUS_RUNS_URL, params)
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    out: Dict[int, Dict[str, Dict[str, Optional[float]]]] = {}
    for n, hv in zip(lead_days, hourly_vars):
        lead = 24 * n
        out[lead] = {}
        for slot, om_id in zip(models, om):
            vals = _series(hourly, hv, om_id, len(om))
            if vals is not None:
                out[lead][slot] = _aggregate_hourly(times, vals, v["agg"], offset_hours)
    return {"url": url, "checksum": _checksum(raw), "by_lead": out}


def fetch_era5(region: Dict[str, Any], variable: str, start: date, end: date) -> Dict[str, Any]:
    _require_enabled()
    v = VARIABLES[variable]
    params = {"latitude": region["lat"], "longitude": region["lon"], "daily": v["daily"], "models": "era5",
              "start_date": start.isoformat(), "end_date": end.isoformat(), "timezone": LOCAL_TZ,
              "wind_speed_unit": "ms", "precipitation_unit": "mm"}
    data, url, raw = HTTP_GET(settings.OPEN_METEO_ARCHIVE_URL, params)
    daily = data.get("daily") or {}
    vals = _series(daily, v["daily"], "era5", 1)
    if vals is None:
        vals = daily.get(v["daily"], [])
    truth = {d: _clean(x) for d, x in zip(daily.get("time") or [], vals or [])}
    return {"url": url, "checksum": _checksum(raw), "truth": truth}


# ------------------------------------------------------------------------------------------ persist
def _register_dataset(db, dataset_id: str, name: str, variable: str, fmt_url: str, checksum: str, n: int,
                      badge: str, start: Optional[datetime], end: Optional[datetime], meta: Dict[str, Any]):
    from app.models.dataset import DatasetRegistry
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if ds is None:
        ds = DatasetRegistry(dataset_id=dataset_id)
        db.add(ds)
    ds.name = name
    ds.source = "OPEN_METEO"
    ds.version = "live"
    ds.license = "CC BY 4.0 (Open-Meteo, non-commercial free tier)"
    ds.format = "API_JSON"
    ds.variables = [variable]
    ds.spatial_coverage = meta.get("region_id", "POINT")
    ds.temporal_coverage_start = start
    ds.temporal_coverage_end = end
    ds.resolution = "point (nearest grid cell)"
    ds.checksum = checksum
    ds.record_count = n
    ds.file_path = fmt_url
    ds.status = "AVAILABLE"
    ds.provenance_badge = badge
    ds.metadata_json = meta
    return ds


def _day_dt(d: str) -> datetime:
    # daily aggregates are local (IST) days; stored as naive UTC midnight of that date for indexing
    return datetime.strptime(d[:10], "%Y-%m-%d")


def store_forecast(db, fc: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a fetch as one dataset + CanonicalWeatherEntity rows (one issue per fetch)."""
    from app.models.canonical_record import CanonicalWeatherEntity
    region = fc["region"]
    fetched = datetime.fromisoformat(fc["fetched_at"])
    issue = fetched.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    stamp = issue.strftime("%Y%m%dT%H")
    dataset_id = f"LIVE_OM_{region['region_id']}_{fc['variable']}_{stamp}"[:100]
    rows = 0
    # idempotent within the same hour
    db.query(CanonicalWeatherEntity).filter(CanonicalWeatherEntity.dataset_id == dataset_id).delete()
    dates = []
    for slot, pts in fc["series"].items():
        om_id = LIVE_MODELS[slot]["open_meteo_id"]
        for p in pts:
            if p["value"] is None:
                continue
            dates.append(p["date"])
            db.add(CanonicalWeatherEntity(
                id=_rid(dataset_id, slot, p["lead_hours"]),
                dataset_id=dataset_id, ingestion_id=dataset_id,
                forecast_time=issue, issue_time=issue, valid_time=_day_dt(p["date"]),
                latitude=region["lat"], longitude=region["lon"], region_id=region["region_id"],
                variable=fc["variable"], lead_time=p["lead_hours"], value=p["value"], unit=fc["unit"],
                model_id=slot, model_version="latest", source=f"OPEN_METEO:{om_id}",
                resolution=LIVE_MODELS[slot]["resolution"], quality_flag="PASSED",
                provenance="PUBLIC_API_FORECAST",
            ))
            rows += 1
    _register_dataset(
        db, dataset_id, f"Open-Meteo live forecast · {region['name']} · {fc['variable']}", fc["variable"],
        fc["url"], fc["checksum"], rows, "PUBLIC_API_FORECAST",
        _day_dt(min(dates)) if dates else None, _day_dt(max(dates)) if dates else None,
        {"region_id": region["region_id"], "fetched_at": fc["fetched_at"], "models": list(fc["series"].keys()),
         "missing": fc["missing"], "grid": fc["grid"], "aggregate": fc["aggregate"], "attribution": ATTRIBUTION,
         "note": fc["note"]},
    )
    db.commit()
    return {"dataset_id": dataset_id, "records": rows, "issue_time": issue.isoformat() + "Z"}


# ------------------------------------------------------------------------------------------ backfill
def _mae(errs: List[float]) -> Optional[float]:
    return round(sum(abs(e) for e in errs) / len(errs), 3) if errs else None


def backfill(db, region_id: str, variable: str = "rainfall", models: Optional[List[str]] = None, days: int = 45,
             lead_days: Iterable[int] = (1, 2), end: Optional[date] = None, truth_source: str = "AUTO") -> Dict[str, Any]:
    """
    Build real verification history: previous-run forecasts vs observed truth.
    Truth: IMD gridded data (rainfall / Tmax, India-first) when truth_source is AUTO or IMD_GRIDDED;
    ERA5 for wind, or when IMD is unreachable (AUTO falls back and says so in `truth_note`).
    Writes VerificationResult (per model/day/lead), ModelSkill (MAE/RMSE/BIAS), reference rows, and fits a
    bias-corrected stacker for the model set. Returns an honest score card (chronological 70/30 hold-out).
    """
    from app.models.canonical_record import CanonicalWeatherEntity
    from app.models.skill import ModelSkill
    from app.models.verification import VerificationResult
    from app.services import india_sources as ind

    models = list(models or DEFAULT_LIVE_MODELS)
    region = resolve_region(db, region_id)
    days = max(10, min(int(days), 365))
    unit = VARIABLES[variable]["unit"]
    rid = region["region_id"]
    truth_source = (truth_source or "AUTO").upper()
    today = datetime.now(timezone.utc).date()

    truth_note, ref = "", None
    if truth_source in ("AUTO", "IMD_GRIDDED") and variable in ind.IMD_VARIABLES:
        t_end = end or (today - timedelta(days=ind.IMD_REALTIME_LAG_DAYS))
        t_start = t_end - timedelta(days=days - 1)
        try:
            imd = ind.fetch_imd_truth(region, variable, t_start, t_end)
            ref = {"truth": imd["truth"], "url": imd["url"], "checksum": imd["checksum"], "model_id": "OBS_IMD",
                   "source": "IMD_PUNE:gridded", "provenance": "OBSERVATION_GRIDDED", "period": BACKFILL_PERIOD_IMD,
                   "resolution": "0.25 deg" if variable == "rainfall" else "1.0/0.5 deg",
                   "name": "IMD gridded observations", "note": imd["note"], "missing": imd["missing"],
                   "attribution": ind.ATTRIBUTION_IMD, "badge": "OBSERVATION_GRIDDED"}
            start, end = t_start, t_end
        except ind.IndiaSourceError as exc:
            if truth_source == "IMD_GRIDDED":
                raise LiveSourceError(f"IMD gridded truth unavailable: {exc}")
            truth_note = f"IMD gridded data unavailable ({exc}); fell back to ERA5."
    elif truth_source == "IMD_GRIDDED":
        raise LiveSourceError(f"IMD gridded data has no '{variable}' product; use ERA5 for wind.")
    if ref is None:
        end = end or (today - timedelta(days=ERA5_LATENCY_DAYS))
        start = end - timedelta(days=days - 1)
        era = fetch_era5(region, variable, start, end)
        ref = {"truth": era["truth"], "url": era["url"], "checksum": era["checksum"], "model_id": "OBS_ERA5",
               "source": "OPEN_METEO:era5", "provenance": "REANALYSIS_REFERENCE", "period": BACKFILL_PERIOD,
               "resolution": "0.25 deg", "name": "ERA5 reference",
               "note": "Reanalysis, not station observation. ~5 day latency.", "missing": [],
               "attribution": ATTRIBUTION, "badge": "REANALYSIS_REFERENCE"}
        if variable == "wind_speed" and not truth_note:
            truth_note = "IMD gridded data has no wind product; ERA5 used."

    offset = settings.IMD_RAIN_DAY_OFFSET_HOURS if (ref["model_id"] == "OBS_IMD" and variable == "rainfall") else 0
    prev = fetch_previous_runs(region, variable, models, start, end, lead_days, offset_hours=offset)
    truth = ref["truth"]
    period = ref["period"]

    # Idempotent: replace earlier backfill rows (any truth) for this region/variable/window
    lo, hi = _day_dt(start.isoformat()), _day_dt(end.isoformat()) + timedelta(days=1)
    db.query(VerificationResult).filter(
        VerificationResult.region_id == rid, VerificationResult.variable == variable,
        VerificationResult.evaluation_window.in_(BACKFILL_PERIODS),
        VerificationResult.verification_time >= lo, VerificationResult.verification_time < hi).delete(synchronize_session=False)

    ref_ds = f"REF_{ref['model_id']}_{rid}_{variable}"[:100]
    db.query(CanonicalWeatherEntity).filter(CanonicalWeatherEntity.dataset_id == ref_ds).delete()
    n_obs = 0
    for d, o in truth.items():
        if o is None:
            continue
        db.add(CanonicalWeatherEntity(
            id=_rid(ref_ds, d), dataset_id=ref_ds, ingestion_id=ref_ds, forecast_time=_day_dt(d),
            issue_time=_day_dt(d), valid_time=_day_dt(d), latitude=region["lat"], longitude=region["lon"],
            region_id=rid, variable=variable, lead_time=0, value=o, unit=unit, model_id=ref["model_id"],
            model_version=ref["model_id"], source=ref["source"], resolution=ref["resolution"], quality_flag="PASSED",
            provenance=ref["provenance"]))
        n_obs += 1
    _register_dataset(db, ref_ds, f"{ref['name']} · {region['name']} · {variable}", variable, ref["url"],
                      ref["checksum"], n_obs, ref["badge"], _day_dt(start.isoformat()), _day_dt(end.isoformat()),
                      {"region_id": rid, "note": ref["note"], "attribution": ref["attribution"],
                       "missing_days": ref["missing"][:30]})
    if ref["model_id"] == "OBS_IMD":
        from app.models.dataset import DatasetRegistry
        ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == ref_ds).first()
        if ds is not None:
            ds.source, ds.license = "IMD_PUNE", "IMD open gridded data (cite IMD; imdlib MIT)"

    report: Dict[str, Any] = {"region": region, "variable": variable, "unit": unit, "window": [start.isoformat(), end.isoformat()],
                              "truth": ref["model_id"], "truth_name": ref["name"], "truth_note": truth_note or ref["note"],
                              "day_window_offset_hours": offset, "truth_missing_days": len(ref["missing"]),
                              "sources": {"previous_runs_url": prev["url"], "truth_url": ref["url"]},
                              "leads": {}, "verification_rows": 0, "observations": n_obs,
                              "attribution": f"{ATTRIBUTION} {ref['attribution'] if ref['model_id'] == 'OBS_IMD' else ''}".strip()}
    from app.intelligence.stacking import fit_stacker_from_rows, BiasCorrectedStacker

    for lead, per_model in prev["by_lead"].items():
        errs: Dict[str, List[float]] = defaultdict(list)
        stack_rows: List[Dict[str, Any]] = []
        for d in sorted(truth):
            o = truth[d]
            if o is None:
                continue
            fcs = {m: per_model.get(m, {}).get(d) for m in models}
            for m, f in fcs.items():
                if f is None:
                    continue
                errs[m].append(f - o)
                db.add(VerificationResult(
                    region_id=rid, variable=variable, lead_hours=lead, model_id=m, method="INDIVIDUAL_MODEL",
                    metric="MAE", forecast_value=f, observed_value=o, score=round(abs(f - o), 3),
                    evaluation_window=period, verification_time=_day_dt(d) + timedelta(hours=12)))
                report["verification_rows"] += 1
            stack_rows.append({"date": d, "forecasts": fcs, "observation": o, "weather_regime": "ALL", "lead_hours": lead})

        skills = {}
        for m, e in errs.items():
            n = len(e)
            mae = _mae(e)
            rmse = round(math.sqrt(sum(x * x for x in e) / n), 3)
            bias = round(sum(e) / n, 3)
            skills[m] = {"MAE": mae, "RMSE": rmse, "BIAS": bias, "n": n}
            for metric, val in (("MAE", mae), ("RMSE", rmse), ("BIAS", bias)):
                row = (db.query(ModelSkill).filter(ModelSkill.model_id == m, ModelSkill.region_id == rid,
                                                   ModelSkill.variable == variable, ModelSkill.lead_hours == lead,
                                                   ModelSkill.metric == metric,
                                                   ModelSkill.evaluation_period.in_(BACKFILL_PERIODS)).first())
                if row is None:
                    row = ModelSkill(model_id=m, region_id=rid, variable=variable, lead_hours=lead, season="ALL",
                                     weather_regime="ALL", metric=metric, evaluation_period=period)
                    db.add(row)
                row.evaluation_period = period
                row.value = val
                row.sample_count = n
                row.updated_at = datetime.now(timezone.utc)

        # Honest hold-out score card on days where every usable model has a value
        usable = [m for m in models if len(errs.get(m, [])) >= max(5, int(0.8 * len(stack_rows)))]
        complete = [r for r in stack_rows if all(r["forecasts"].get(m) is not None for m in usable)]
        card: Dict[str, Any] = {"models_used": usable, "complete_days": len(complete), "per_model": skills}
        if len(usable) >= 2 and len(complete) >= 14:
            cut = int(len(complete) * 0.7)
            train, test = complete[:cut], complete[cut:]
            st = BiasCorrectedStacker(models=usable, min_cell=10, shrinkage=20.0)
            st.nonnegative = variable != "temperature"
            st.lead_fallback = True
            st.fit(train)
            avg_e, stk_e = [], []
            model_e: Dict[str, List[float]] = defaultdict(list)
            for r in test:
                o = r["observation"]
                fv = [r["forecasts"][m] for m in usable]
                avg_e.append(sum(fv) / len(fv) - o)
                p = st.predict(r["forecasts"], "ALL", lead)["value"] if st.is_fitted else None
                if p is not None:
                    stk_e.append(p - o)
                for m in usable:
                    model_e[m].append(r["forecasts"][m] - o)
            best_m = min(model_e, key=lambda m: _mae(model_e[m]))
            card["holdout"] = {
                "train_days": len(train), "test_days": len(test),
                "simple_average_mae": _mae(avg_e), "stacking_mae": _mae(stk_e) if stk_e else None,
                "best_single_model": best_m, "best_single_model_mae": _mae(model_e[best_m]),
                "note": "Chronological split; small samples - treat as indicative, not a skill claim.",
            }
            fitted = fit_stacker_from_rows(rid, variable, usable, complete, f"FITTED_ON_{period}")
            card["stacker"] = "fitted on all complete days" if fitted else "not fitted (too few rows)"
        else:
            card["holdout"] = None
            card["stacker"] = "not fitted (need >= 2 models and >= 14 complete days)"
        report["leads"][str(lead)] = card

    db.commit()
    return report


def refit_stackers_from_db(db) -> int:
    """Re-create region-fitted stackers from stored backfill rows (called at start-up). Returns count."""
    from app.models.verification import VerificationResult
    from app.intelligence.stacking import fit_stacker_from_rows
    q = (db.query(VerificationResult)
         .filter(VerificationResult.evaluation_window.in_(BACKFILL_PERIODS),
                 VerificationResult.method == "INDIVIDUAL_MODEL")
         .order_by(VerificationResult.verification_time.asc()))
    groups: Dict[Tuple[str, str], Dict[Tuple[int, str], Dict[str, Any]]] = defaultdict(dict)
    for r in q.yield_per(2000):
        key = (r.region_id, r.variable)
        cell = groups[key].setdefault((r.lead_hours, r.verification_time.date().isoformat()),
                                      {"forecasts": {}, "observation": r.observed_value, "weather_regime": "ALL",
                                       "lead_hours": r.lead_hours})
        cell["forecasts"][r.model_id] = r.forecast_value
    count = 0
    for (rid, var), cells in groups.items():
        rows = list(cells.values())
        freq: Dict[str, int] = defaultdict(int)
        for row in rows:
            for m in row["forecasts"]:
                freq[m] += 1
        usable = [m for m, c in freq.items() if c >= 0.8 * len(rows)]
        if len(usable) >= 2 and fit_stacker_from_rows(rid, var, usable, rows, "FITTED_ON_VERIFIED_BACKFILL"):
            count += 1
    return count


def latest_live_issue(db, region_id: str, variable: str, lead_hours: int, max_age_hours: int = 36) -> Optional[datetime]:
    from sqlalchemy import func
    from app.models.canonical_record import CanonicalWeatherEntity
    latest = (db.query(func.max(CanonicalWeatherEntity.issue_time))
              .filter(CanonicalWeatherEntity.region_id == region_id, CanonicalWeatherEntity.variable == variable,
                      CanonicalWeatherEntity.lead_time == lead_hours,
                      CanonicalWeatherEntity.provenance == "PUBLIC_API_FORECAST").scalar())
    if latest is None:
        return None
    if datetime.now(timezone.utc).replace(tzinfo=None) - latest > timedelta(hours=max_age_hours):
        return None
    return latest


def source_catalog() -> Dict[str, Any]:
    ok, why = live_enabled()
    return {
        "enabled": ok, "status": why, "attribution": ATTRIBUTION,
        "public_models": [{"slot": k, **v} for k, v in LIVE_MODELS.items()],
        "restricted_models": [{"slot": k, "how_to_get": v} for k, v in RESTRICTED_SOURCES.items()],
        "reference": {"id": "OBS_ERA5", "name": "ERA5 reanalysis (Copernicus/ECMWF via Open-Meteo)",
                      "latency_days": ERA5_LATENCY_DAYS,
                      "note": "Reanalysis used as verification truth; not a rain-gauge observation."},
        "variables": {k: {"aggregate": v["daily"], "unit": v["unit"]} for k, v in VARIABLES.items()},
        "endpoints": {"forecast": settings.OPEN_METEO_FORECAST_URL, "previous_runs": settings.OPEN_METEO_PREVIOUS_RUNS_URL,
                      "archive": settings.OPEN_METEO_ARCHIVE_URL},
        "licence": "Free tier: non-commercial use with attribution (CC BY 4.0). Commercial use needs an API key.",
    }
