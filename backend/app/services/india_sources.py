"""
India-first data sources for VARUNA (SIH26081 · MoES / NCMRWF).

Tier 1 — Indian sources (preferred):
  * IMD gridded daily data (IMD Pune) — the verification truth for Indian rainfall and Tmax.
      rainfall 0.25 deg (Pai et al. 2014 product), Tmax 1.0 deg archive / 0.5 deg real-time.
      Public, no login. Download endpoints and binary layout follow the open-source `imdlib`
      package (MIT, Nandi et al. 2022, doi:10.5281/zenodo.7205414).
      If the backend host cannot reach imdpune.gov.in, download the .grd files in a browser and
      upload them (POST /api/india/imd-grid/upload) — the same parser is used.
  * IMD API (api.imd.gov.in/api/v1) — station observations, district rainfall, district warnings,
      city forecasts. Access is granted by IMD (contact the nodal officer listed in IMD's API doc);
      this adapter stays dormant until IMD_API_ENABLED=true.
  * NCMRWF products (NCUM-G/R, NEPS) — institutional access. Files placed in NCMRWF_DROP_DIR are
      ingested with provenance AUTHORIZED_OPERATIONAL_FEED (de-duplicated by SHA-256).
Tier 2 — global public models over India (Open-Meteo): see live_sources.py (reference / gap-filler).
Tier 3 — synthetic demo.

Nothing here runs network I/O at import time; HTTP goes through IMD_HTTP_POST / IMD_HTTP_GET so tests
can replace it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings

logger = logging.getLogger("varuna.india")


class IndiaSourceError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- IMD gridded data
# Layouts as used by imdlib (core.py / real.py). Values are float32, C order (day, lat, lon).
GRID_SPECS: Dict[str, Dict[str, Any]] = {
    "rain": {"lat0": 6.5, "lat1": 38.5, "nlat": 129, "lon0": 66.5, "lon1": 100.0, "nlon": 135,
             "missing": -999.0, "res": "0.25 deg"},
    "tmax_archive": {"lat0": 7.5, "lat1": 37.5, "nlat": 31, "lon0": 67.5, "lon1": 97.5, "nlon": 31,
                     "missing": 99.9, "res": "1.0 deg"},
    "tmax_realtime": {"lat0": 7.5, "lat1": 37.5, "nlat": 61, "lon0": 67.5, "lon1": 97.5, "nlon": 61,
                      "missing": 99.9, "res": "0.5 deg"},
}
IMD_ENDPOINTS = {
    ("rainfall", "archive"): ("https://imdpune.gov.in/cmpg/Griddata/rainfall.php", "rain"),
    ("temperature", "archive"): ("https://imdpune.gov.in/cmpg/Griddata/maxtemp.php", "maxtemp"),
    ("rainfall", "realtime"): ("https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php", "rain"),
    ("temperature", "realtime"): ("https://imdpune.gov.in/cmpg/Realtimedata/max/max.php", "max"),
}
IMD_VARIABLES = {"rainfall", "temperature"}  # IMD gridded has no wind product
IMD_REALTIME_LAG_DAYS = 2
# IMD daily rainfall is the 24 h accumulation ending 08:30 IST (03 UTC). VARUNA assigns it to the day the
# accumulation *starts* (08:30 IST D -> 08:30 IST D+1) and aggregates model hours on the same window.
# Set IMD_RAIN_DAY_OFFSET_HOURS=-15 if your files follow the "ending on D" convention instead.
ATTRIBUTION_IMD = ("IMD gridded data (India Meteorological Department, Pune); download/format per imdlib "
                   "(Nandi et al., 2022, MIT).")


def _default_post(url: str, data: Dict[str, Any]) -> bytes:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"User-Agent": "VARUNA-forecast-intelligence/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=settings.LIVE_HTTP_TIMEOUT_SECONDS * 3) as r:
            return r.read()
    except Exception as exc:
        raise IndiaSourceError(f"IMD Pune request failed ({url}): {exc}") from exc


IMD_HTTP_POST: Callable[[str, Dict[str, Any]], bytes] = _default_post


def _grid_dir() -> str:
    d = os.path.join(settings.DATA_STORAGE_PATH, "imd_grid")
    os.makedirs(d, exist_ok=True)
    return d


def _spec(variable: str, kind: str) -> Dict[str, Any]:
    if variable == "rainfall":
        return GRID_SPECS["rain"]
    return GRID_SPECS["tmax_archive" if kind == "archive" else "tmax_realtime"]


def _cache_name(variable: str, kind: str, key: str) -> str:
    return os.path.join(_grid_dir(), f"{variable}_{kind}_{key}.grd")


def parse_grid(raw: bytes, variable: str, kind: str, n_days: Optional[int] = None) -> np.ndarray:
    """Binary .grd -> array (days, nlat, nlon) with NaN for missing cells."""
    sp = _spec(variable, kind)
    cells = sp["nlat"] * sp["nlon"]
    arr = np.frombuffer(raw, dtype="<f4")
    if arr.size % cells != 0:
        raise IndiaSourceError(f"{variable} {kind} file has {arr.size} values, not a multiple of the "
                               f"{sp['nlat']}x{sp['nlon']} grid — wrong file type or truncated download.")
    days = arr.size // cells
    if n_days is not None and days != n_days:
        raise IndiaSourceError(f"Expected {n_days} day(s) in the {variable} {kind} file, found {days}.")
    grid = arr.reshape(days, sp["nlat"], sp["nlon"]).astype("float64")
    miss = sp["missing"]
    grid[np.isclose(grid, miss) | (grid <= -998.0) | (grid > 1e6)] = np.nan
    if variable == "temperature":
        grid[(grid > 60) | (grid < -60)] = np.nan
    return grid


def grid_point(grid2d: np.ndarray, variable: str, kind: str, lat: float, lon: float) -> Tuple[Optional[float], Dict[str, Any]]:
    """Nearest valid cell to (lat, lon), searching up to 2 cells out (coastal centroids may fall on sea)."""
    sp = _spec(variable, kind)
    lats = np.linspace(sp["lat0"], sp["lat1"], sp["nlat"])
    lons = np.linspace(sp["lon0"], sp["lon1"], sp["nlon"])
    if not (lats[0] - 1 <= lat <= lats[-1] + 1 and lons[0] - 1 <= lon <= lons[-1] + 1):
        raise IndiaSourceError("Location is outside the IMD India grid.")
    i0, j0 = int(np.abs(lats - lat).argmin()), int(np.abs(lons - lon).argmin())
    best = None
    for r in range(0, 3):
        for i in range(max(0, i0 - r), min(sp["nlat"], i0 + r + 1)):
            for j in range(max(0, j0 - r), min(sp["nlon"], j0 + r + 1)):
                v = grid2d[i, j]
                if not math.isnan(v):
                    d = (lats[i] - lat) ** 2 + (lons[j] - lon) ** 2
                    if best is None or d < best[0]:
                        best = (d, i, j, v)
        if best:
            break
    if best is None:
        return None, {"cell": None}
    _, i, j, v = best
    return round(float(v), 2), {"cell_lat": float(lats[i]), "cell_lon": float(lons[j]), "resolution": sp["res"]}


def _load_archive_year(variable: str, year: int) -> Tuple[np.ndarray, str]:
    path = _cache_name(variable, "archive", str(year))
    if not os.path.exists(path) or os.path.getsize(path) < 1024:
        url, key = IMD_ENDPOINTS[(variable, "archive")]
        raw = IMD_HTTP_POST(url, {key: year})
        with open(path, "wb") as f:
            f.write(raw)
    with open(path, "rb") as f:
        raw = f.read()
    days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
    return parse_grid(raw, variable, "archive", days), path


def _load_realtime_day(variable: str, d: date) -> Tuple[np.ndarray, str]:
    path = _cache_name(variable, "realtime", d.strftime("%Y%m%d"))
    if not os.path.exists(path) or os.path.getsize(path) < 1024:
        url, key = IMD_ENDPOINTS[(variable, "realtime")]
        raw = IMD_HTTP_POST(url, {key: d.strftime("%d%m%Y")})
        with open(path, "wb") as f:
            f.write(raw)
    with open(path, "rb") as f:
        raw = f.read()
    return parse_grid(raw, variable, "realtime", 1)[0], path


def imd_enabled() -> Tuple[bool, str]:
    if settings.AIR_GAPPED_MODE:
        return False, "AIR_GAPPED_MODE is on: only uploaded IMD files are used."
    return True, "enabled"


def fetch_imd_truth(region: Dict[str, Any], variable: str, start: date, end: date) -> Dict[str, Any]:
    """
    Daily IMD gridded values at the region centroid. Uses the yearly archive for complete past years and
    the real-time daily files for the current year. Cached on disk; uploaded files are picked up the same way.
    """
    if variable not in IMD_VARIABLES:
        raise IndiaSourceError(f"IMD gridded data has no '{variable}' product (rainfall and Tmax only).")
    online, _ = imd_enabled()
    today = datetime.now(timezone.utc).date()
    truth: Dict[str, Optional[float]] = {}
    files, missing, cells = set(), [], {}
    year_cache: Dict[int, Tuple[np.ndarray, str]] = {}
    d = start
    while d <= end:
        try:
            if d.year < today.year:
                if d.year not in year_cache:
                    if not online and not os.path.exists(_cache_name(variable, "archive", str(d.year))):
                        raise IndiaSourceError("offline and no uploaded archive file")
                    year_cache[d.year] = _load_archive_year(variable, d.year)
                grid, path = year_cache[d.year]
                g2 = grid[d.timetuple().tm_yday - 1]
                kind = "archive"
            else:
                if not online and not os.path.exists(_cache_name(variable, "realtime", d.strftime("%Y%m%d"))):
                    raise IndiaSourceError("offline and no uploaded real-time file")
                g2, path = _load_realtime_day(variable, d)
                kind = "realtime"
            v, cell = grid_point(g2, variable, kind, region["lat"], region["lon"])
            truth[d.isoformat()] = v
            files.add(os.path.basename(path))
            cells[kind] = cell
        except IndiaSourceError as exc:
            missing.append({"date": d.isoformat(), "reason": str(exc)[:160]})
        d += timedelta(days=1)
    if not any(v is not None for v in truth.values()):
        reason = missing[0]["reason"] if missing else "no data"
        raise IndiaSourceError(f"No IMD gridded {variable} for {start}..{end}: {reason}")
    raw_sig = json.dumps(truth, sort_keys=True).encode()
    return {"truth": truth, "missing": missing, "files": sorted(files), "cells": cells,
            "url": "https://imdpune.gov.in/cmpg/Griddata/ (archive) · /cmpg/Realtimedata/ (real-time)",
            "checksum": hashlib.sha256(raw_sig).hexdigest(), "reference": "OBS_IMD",
            "note": ("Rainfall day = 08:30 IST D -> 08:30 IST D+1; model hours are aggregated on the same window."
                     if variable == "rainfall" else "Daily maximum temperature on day D.")}


def save_uploaded_grid(raw: bytes, variable: str, kind: str, key: str) -> Dict[str, Any]:
    """Validate and cache a user-uploaded IMD .grd file (key = YYYY for archive, YYYY-MM-DD for real-time)."""
    if variable not in IMD_VARIABLES:
        raise IndiaSourceError("variable must be rainfall or temperature")
    if kind == "archive":
        year = int(key)
        days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
        grid = parse_grid(raw, variable, "archive", days)
        path = _cache_name(variable, "archive", str(year))
    else:
        d = date.fromisoformat(key)
        grid = parse_grid(raw, variable, "realtime", 1)
        path = _cache_name(variable, "realtime", d.strftime("%Y%m%d"))
    with open(path, "wb") as f:
        f.write(raw)
    valid = int(np.isfinite(grid).sum())
    return {"stored_as": os.path.basename(path), "days": int(grid.shape[0]), "valid_cells": valid,
            "sha256": hashlib.sha256(raw).hexdigest()}


# ----------------------------------------------------------------------------- IMD API (api.imd.gov.in)
# Endpoints from IMD's public API reference (https://api.imd.gov.in/public/api_reference.html).
IMD_API_ENDPOINTS = {
    "current_wx": "current_wx",            # ?id=<station id>   station observation incl. last-24 h rainfall
    "city_forecast": "cityforecastloc",    # ?id=<station id>   7-day city forecast with lat/lon
    "district_rainfall": "districtrainfall",  # ?id=<district obj id>
    "district_warning": "districtwarning",    # ?id=<district obj id>  Day_1..Day_5 + colours
}
# Default region -> IMD station (WMO index) near the subdivision centroid. **Verify with IMD** and override
# with IMD_STATION_MAP='{"IN_TELANGANA_DECCAN": {"station": "43128", "district": "..."}}'.
DEFAULT_STATION_MAP: Dict[str, Dict[str, str]] = {
    "IN_TELANGANA_DECCAN": {"station": "43128", "name": "Hyderabad"},
    "IN_TELANGANA_HYDERABAD": {"station": "43128", "name": "Hyderabad"},
    "IN_KONKAN_GOA": {"station": "43003", "name": "Mumbai (Santacruz)"},
    "IN_GANGETIC_WB": {"station": "42807", "name": "Kolkata (Alipore)"},
    "IN_ODISHA_COASTAL": {"station": "42971", "name": "Bhubaneswar"},
    "IN_ASSAM_VALLEY": {"station": "42410", "name": "Guwahati"},
    "IN_VIDARBHA_CENTRAL": {"station": "42867", "name": "Nagpur"},
    "IN_JAMMU_KASHMIR": {"station": "42027", "name": "Srinagar"},
    "IN_WEST_RAJASTHAN": {"station": "42339", "name": "Jodhpur"},
}


def station_map() -> Dict[str, Dict[str, str]]:
    m = dict(DEFAULT_STATION_MAP)
    if settings.IMD_STATION_MAP:
        try:
            m.update(json.loads(settings.IMD_STATION_MAP))
        except ValueError:
            logger.warning("IMD_STATION_MAP is not valid JSON; using defaults")
    return m


def _default_api_get(url: str, params: Dict[str, Any]) -> Any:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": "VARUNA-forecast-intelligence/1.0", "Accept": "application/json"}
    if settings.IMD_API_KEY:
        headers[settings.IMD_API_KEY_HEADER] = settings.IMD_API_KEY
    req = urllib.request.Request(full, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=settings.LIVE_HTTP_TIMEOUT_SECONDS) as r:
            raw = r.read()
    except Exception as exc:
        raise IndiaSourceError(f"IMD API request failed ({url}): {exc}. IMD grants API access per organisation "
                               "(often by whitelisting the server IP) — check with the IMD nodal officer.") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise IndiaSourceError("IMD API returned non-JSON (access not granted for this IP/key?)") from exc


IMD_API_GET: Callable[[str, Dict[str, Any]], Any] = _default_api_get


def imd_api_status() -> Tuple[bool, str]:
    if settings.AIR_GAPPED_MODE:
        return False, "AIR_GAPPED_MODE is on."
    if not settings.IMD_API_ENABLED:
        return False, "Not configured: set IMD_API_ENABLED=true once IMD has granted access (and IMD_API_KEY if issued)."
    return True, "enabled"


def _num(row: Dict[str, Any], *keys: str) -> Optional[float]:
    """Tolerant field lookup: exact key, then case/space/underscore-insensitive match."""
    norm = {"".join(ch for ch in k.lower() if ch.isalnum()): v for k, v in row.items()}
    for k in keys:
        v = row.get(k)
        if v is None:
            v = norm.get("".join(ch for ch in k.lower() if ch.isalnum()))
        if v in (None, "", "NA", "--", "-"):
            continue
        try:
            f = float(str(v).replace("TRACE", "0").replace("Trace", "0"))
        except ValueError:
            continue
        if not math.isnan(f):
            return f
    return None


def _rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for k in ("data", "result", "results", "records"):
            if isinstance(payload.get(k), list):
                return [r for r in payload[k] if isinstance(r, dict)]
        return [payload]
    return []


def imd_station_observation(region_id: str) -> Dict[str, Any]:
    """Latest IMD station observation for the region's mapped station (last-24 h rain, temperature, wind)."""
    ok, why = imd_api_status()
    if not ok:
        raise IndiaSourceError(why)
    st = station_map().get(region_id)
    if not st:
        raise IndiaSourceError(f"No IMD station mapped for {region_id}; add it to IMD_STATION_MAP.")
    url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/{IMD_API_ENDPOINTS['current_wx']}"
    rows = _rows(IMD_API_GET(url, {"id": st["station"]}))
    if not rows:
        raise IndiaSourceError("IMD API returned no observation rows.")
    r = rows[0]
    wind_kmph = _num(r, "Wind Speed KMPH", "Wind Speed", "WindSpeed")
    return {
        "station_id": st["station"], "station": r.get("Station") or st.get("name"),
        "observed_date": r.get("Date of Observation") or r.get("Date"),
        "observed_time_utc": r.get("Time of Observation") or r.get("Time"),
        "rainfall_24h_mm": _num(r, "Last 24 hrs Rainfall", "Past_24_hrs_Rainfall", "Rainfall"),
        "temperature_c": _num(r, "Temperature", "Temp"),
        "wind_speed_ms": round(wind_kmph / 3.6, 2) if wind_kmph is not None else None,
        "source": f"IMD_API:{IMD_API_ENDPOINTS['current_wx']}?id={st['station']}", "raw": r,
    }


def imd_district_warning(district_id: str) -> Dict[str, Any]:
    ok, why = imd_api_status()
    if not ok:
        raise IndiaSourceError(why)
    url = f"{settings.IMD_API_BASE_URL.rstrip('/')}/{IMD_API_ENDPOINTS['district_warning']}"
    rows = _rows(IMD_API_GET(url, {"id": district_id}))
    if not rows:
        raise IndiaSourceError("IMD API returned no warning rows.")
    r = rows[0]
    colour = {"1": "GREEN", "2": "YELLOW", "3": "ORANGE", "4": "RED"}
    days = []
    for n in range(1, 6):
        c = r.get(f"Day{n}_Color") or r.get(f"Day_{n}_Color")
        days.append({"day": n, "warning_codes": r.get(f"Day_{n}"), "colour": colour.get(str(c), c)})
    return {"district": r.get("District"), "date": r.get("Date"), "days": days,
            "source": f"IMD_API:{IMD_API_ENDPOINTS['district_warning']}?id={district_id}", "raw": r}


# ----------------------------------------------------------------------------- NCMRWF drop folder
NCMRWF_MODEL_HINTS = (("NEPS", "NCUM"), ("NCUM_R", "NCUM"), ("NCUMR", "NCUM"), ("NCUM", "NCUM"),
                      ("IMDGFS", "GFS"), ("GFS", "GFS"), ("WRF", "WRF"))
INGESTIBLE = (".csv", ".json", ".jsonl", ".parquet", ".nc", ".nc4", ".netcdf", ".zip", ".geojson")


def scan_ncmrwf_drop(db) -> Dict[str, Any]:
    """Ingest new files from NCMRWF_DROP_DIR as AUTHORIZED_OPERATIONAL_FEED (SHA-256 de-duplicated)."""
    from app.models.dataset import DatasetRegistry
    from app.services.ingestion import ingestion_engine
    folder = settings.NCMRWF_DROP_DIR
    if not folder:
        raise IndiaSourceError("NCMRWF_DROP_DIR is not set. Point it at the folder where NCMRWF/IMD product files arrive "
                               "(SFTP drop, mounted share or object-storage sync).")
    if not os.path.isdir(folder):
        raise IndiaSourceError(f"NCMRWF_DROP_DIR does not exist: {folder}")
    known = {c for (c,) in db.query(DatasetRegistry.checksum).filter(DatasetRegistry.checksum.isnot(None)).all()}
    results = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isfile(path) or not name.lower().endswith(INGESTIBLE):
            continue
        with open(path, "rb") as f:
            raw = f.read()
        sha = hashlib.sha256(raw).hexdigest()
        if sha in known:
            results.append({"file": name, "status": "SKIPPED_DUPLICATE", "sha256": sha})
            continue
        up = name.upper().replace("-", "_")
        hint = next((m for k, m in NCMRWF_MODEL_HINTS if k in up), None)
        ds_id = f"NCMRWF_{os.path.splitext(name)[0][:80]}_{sha[:8]}"  # same file name, new delivery -> new dataset
        try:
            res = ingestion_engine.ingest_dataset(db=db, dataset_id=ds_id, file_content=raw, filename=name,
                                                  source="NCMRWF / IMD (authorised drop)", version="operational",
                                                  provenance="AUTHORIZED_OPERATIONAL_FEED", persist_records=True)
            results.append({"file": name, "status": "INGESTED", "dataset_id": ds_id, "sha256": sha,
                            "model_hint": hint, "records": (res or {}).get("records_ingested") or (res or {}).get("record_count")})
            known.add(sha)
        except Exception as exc:  # one bad file must not stop the scan
            db.rollback()
            results.append({"file": name, "status": "FAILED", "error": str(exc)[:300], "sha256": sha})
    return {"folder": folder, "files": results}


# ----------------------------------------------------------------------------- catalogue
def india_catalog() -> Dict[str, Any]:
    api_ok, api_why = imd_api_status()
    grid_ok, grid_why = imd_enabled()
    gdir = os.path.join(settings.DATA_STORAGE_PATH, "imd_grid")
    cached = sorted(os.listdir(gdir)) if os.path.isdir(gdir) else []
    return {
        "tiers": ["INDIA_PRIMARY", "GLOBAL_REFERENCE", "SYNTHETIC_DEMO"],
        "india_primary": [
            {"id": "IMD_GRIDDED", "name": "IMD gridded daily rainfall (0.25°) & Tmax", "provider": "IMD Pune",
             "role": "Verification truth for India", "access": "Public, no login",
             "status": "AVAILABLE" if grid_ok else "UPLOAD_ONLY", "detail": grid_why,
             "cached_files": len(cached), "url": "https://imdpune.gov.in/"},
            {"id": "IMD_API", "name": "IMD API — station obs, district rainfall & warnings, city forecasts",
             "provider": "India Meteorological Department", "role": "Observations, IMD warnings for comparison",
             "access": "Granted by IMD (API reference: api.imd.gov.in/public/api_reference.html)",
             "status": "CONFIGURED" if api_ok else "NOT_CONFIGURED", "detail": api_why,
             "url": "https://api.imd.gov.in/"},
            {"id": "NCMRWF_NCUM", "name": "NCMRWF NCUM-G / NCUM-R / NEPS forecasts", "provider": "NCMRWF (MoES)",
             "role": "Primary Indian NWP forecasts", "access": "Institutional request to NCMRWF",
             "status": "CONFIGURED" if settings.NCMRWF_DROP_DIR else "NOT_CONFIGURED",
             "detail": f"Drop folder: {settings.NCMRWF_DROP_DIR}" if settings.NCMRWF_DROP_DIR else
                       "Set NCMRWF_DROP_DIR to ingest delivered files automatically; or upload files.",
             "url": "https://www.ncmrwf.gov.in/"},
            {"id": "IMDAA", "name": "IMDAA regional reanalysis (12 km)", "provider": "NCMRWF RDS",
             "role": "Long verification history", "access": "Free registration (rds.ncmrwf.gov.in)",
             "status": "MANUAL_UPLOAD", "detail": "Download NetCDF and upload.", "url": "https://rds.ncmrwf.gov.in/"},
            {"id": "MOSDAC", "name": "INSAT-3D/3DR satellite rainfall", "provider": "ISRO MOSDAC",
             "role": "Rainfall over sparse-gauge areas / ocean", "access": "Free registration",
             "status": "MANUAL_UPLOAD", "detail": "Download and upload (CSV/NetCDF).", "url": "https://www.mosdac.gov.in/"},
        ],
        "station_map": station_map(),
        "attribution": ATTRIBUTION_IMD,
    }
