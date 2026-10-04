"""
India-first data sources (SIH26081): IMD gridded truth, IMD API, NCMRWF product drop.

  GET  /india/sources                  tiered catalogue (India primary → global reference → synthetic)   (forecast:view)
  POST /india/imd-grid/fetch           IMD gridded daily values at a region centroid                      (live:fetch, audited)
  POST /india/imd-grid/upload          upload an IMD .grd file when imdpune.gov.in is not reachable       (data:ingest, audited)
  GET  /india/imd/observation          latest IMD station observation (needs IMD API access)              (forecast:view)
  GET  /india/imd/district-warning     IMD district warning colours, Day 1–5 (needs IMD API access)       (forecast:view)
  POST /india/ncmrwf/scan              ingest new files from NCMRWF_DROP_DIR                               (data:ingest, audited)
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.models.user import User
from app.services import india_sources as ind
from app.services import live_sources as ls
from app.services.audit_service import record as audit

router = APIRouter(prefix="/india", tags=["India data sources"])


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request and request.client else None


@router.get("/sources")
def sources(_u: User = Depends(get_current_user)):
    cat = ind.india_catalog()
    g = ls.source_catalog()
    cat["global_reference"] = {
        "status": g["status"], "enabled": g["enabled"], "models": g["public_models"],
        "note": "Global models extracted over Indian subdivisions only; used as extra ensemble members and as a "
                "fallback when Indian feeds are missing. Never labelled as NCMRWF/IMD output.",
        "licence": g["licence"], "attribution": g["attribution"],
    }
    cat["restricted"] = g["restricted_models"]
    return cat


class GridFetch(BaseModel):
    region_id: str = "IN_TELANGANA_DECCAN"
    variable: str = "rainfall"
    start: date
    end: Optional[date] = None


@router.post("/imd-grid/fetch")
def imd_grid_fetch(req: GridFetch, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("live:fetch"))):
    try:
        region = ls.resolve_region(db, req.region_id)
        res = ind.fetch_imd_truth(region, req.variable, req.start, req.end or req.start)
    except (ind.IndiaSourceError, ls.LiveSourceError) as exc:
        audit(db, "IMD_GRID_FETCH", "REGION", req.region_id, actor=user, result="FAILED", reason=str(exc)[:500],
              request_ip=_ip(request))
        raise HTTPException(502, f"IMD gridded data unavailable: {exc}")
    audit(db, "IMD_GRID_FETCH", "REGION", region["region_id"], actor=user,
          metadata={"variable": req.variable, "start": str(req.start), "end": str(req.end or req.start),
                    "files": res["files"], "missing": len(res["missing"])}, request_ip=_ip(request))
    return {"region": region, "variable": req.variable, **res}


@router.post("/imd-grid/upload")
async def imd_grid_upload(request: Request, variable: str = Form(..., description="rainfall | temperature"),
                          kind: str = Form(..., description="archive (yearly file) | realtime (daily file)"),
                          key: str = Form(..., description="YYYY for archive, YYYY-MM-DD for realtime"),
                          file: UploadFile = File(...), db: Session = Depends(get_db),
                          user: User = Depends(require_permission("data:ingest"))):
    raw = await file.read()
    try:
        res = ind.save_uploaded_grid(raw, variable, kind, key)
    except (ind.IndiaSourceError, ValueError) as exc:
        audit(db, "IMD_GRID_UPLOAD", "FILE", file.filename, actor=user, result="FAILED", reason=str(exc)[:500])
        raise HTTPException(422, str(exc))
    audit(db, "IMD_GRID_UPLOAD", "FILE", file.filename, actor=user,
          metadata={"variable": variable, "kind": kind, "key": key, **res}, request_ip=_ip(request))
    return res


@router.get("/imd/observation")
def imd_observation(region_id: str, _u: User = Depends(require_permission("forecast:view"))):
    try:
        return ind.imd_station_observation(region_id)
    except ind.IndiaSourceError as exc:
        raise HTTPException(503, str(exc))


@router.get("/imd/district-warning")
def imd_warning(district_id: str, _u: User = Depends(require_permission("forecast:view"))):
    try:
        return ind.imd_district_warning(district_id)
    except ind.IndiaSourceError as exc:
        raise HTTPException(503, str(exc))


@router.post("/ncmrwf/scan")
def ncmrwf_scan(request: Request, db: Session = Depends(get_db), user: User = Depends(require_permission("data:ingest"))):
    try:
        res = ind.scan_ncmrwf_drop(db)
    except ind.IndiaSourceError as exc:
        raise HTTPException(409, str(exc))
    audit(db, "NCMRWF_SCAN", "FOLDER", res["folder"], actor=user,
          metadata={"files": [{k: f.get(k) for k in ("file", "status", "sha256")} for f in res["files"]]},
          request_ip=_ip(request))
    return res
