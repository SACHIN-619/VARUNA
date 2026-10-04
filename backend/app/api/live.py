"""
Live public data (Open-Meteo): catalogue, fetch the latest model forecasts, and backfill verification history.

  GET  /live/sources                  public + restricted sources, licence, status          (forecast:view)
  POST /live/fetch                    fetch & store the latest forecasts for a region        (live:fetch, audited)
  POST /live/backfill                 previous runs vs ERA5 -> verification + skill + stacker (live:fetch, audited)
  GET  /live/datasets                 stored live / reference datasets with URLs + checksums (forecast:view)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.models.user import User
from app.services import live_sources as ls
from app.services.audit_service import record as audit

router = APIRouter(prefix="/live", tags=["Live public data"])


class FetchRequest(BaseModel):
    region_id: str = "IN_TELANGANA_HYDERABAD"
    variables: List[str] = Field(default_factory=lambda: ["rainfall"])
    models: Optional[List[str]] = None
    days: int = Field(4, ge=1, le=10)


class BackfillRequest(BaseModel):
    region_id: str = "IN_TELANGANA_HYDERABAD"
    variable: str = "rainfall"
    models: Optional[List[str]] = None
    days: int = Field(45, ge=10, le=365)
    lead_days: List[int] = Field(default_factory=lambda: [1, 2])
    truth_source: str = Field("AUTO", description="AUTO (IMD gridded, ERA5 fallback) | IMD_GRIDDED | ERA5")


def _check_region(user: User, region_id: str):
    from app.core.permissions import region_allowed
    if not region_allowed(user.region_scope, region_id):
        raise HTTPException(403, f"Region '{region_id}' is outside your data scope.")


@router.get("/sources")
def live_source_catalog(_u: User = Depends(get_current_user)):
    return ls.source_catalog()


@router.post("/fetch")
def live_fetch(req: FetchRequest, request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_permission("live:fetch"))):
    _check_region(user, req.region_id)
    models = req.models or ls.DEFAULT_LIVE_MODELS
    try:
        region = ls.resolve_region(db, req.region_id)
        results = []
        for var in req.variables:
            fc = ls.fetch_forecast(region, var, models, req.days)
            stored = ls.store_forecast(db, fc)
            results.append({"variable": var, **stored, "models_received": list(fc["series"].keys()),
                            "missing": fc["missing"], "fetched_at": fc["fetched_at"], "url": fc["url"],
                            "checksum": fc["checksum"], "grid": fc["grid"], "note": fc["note"]})
    except ls.LiveSourceError as exc:
        audit(db, "LIVE_FETCH", "REGION", req.region_id, actor=user, result="FAILED", reason=str(exc)[:500],
              request_ip=request.client.host if request.client else None)
        raise HTTPException(502, f"Live source unavailable: {exc}")
    audit(db, "LIVE_FETCH", "REGION", region["region_id"], actor=user,
          metadata={"variables": req.variables, "models": models,
                    "datasets": [r["dataset_id"] for r in results], "records": sum(r["records"] for r in results)},
          request_ip=request.client.host if request.client else None)
    return {"region": region, "results": results, "attribution": ls.ATTRIBUTION}


@router.post("/backfill")
def live_backfill(req: BackfillRequest, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("live:fetch"))):
    _check_region(user, req.region_id)
    try:
        report = ls.backfill(db, req.region_id, req.variable, req.models, req.days, req.lead_days,
                             truth_source=req.truth_source)
    except ls.LiveSourceError as exc:
        db.rollback()
        audit(db, "LIVE_BACKFILL", "REGION", req.region_id, actor=user, result="FAILED", reason=str(exc)[:500])
        raise HTTPException(502, f"Live source unavailable: {exc}")
    audit(db, "LIVE_BACKFILL", "REGION", req.region_id, actor=user,
          metadata={"variable": req.variable, "window": report["window"], "rows": report["verification_rows"],
                    "truth": report["truth"],
                    "observations": report["observations"]},
          request_ip=request.client.host if request.client else None)
    return report


@router.get("/datasets")
def live_datasets(limit: int = 50, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    from app.models.dataset import DatasetRegistry
    from sqlalchemy import or_
    rows = (db.query(DatasetRegistry).filter(or_(DatasetRegistry.source.in_(["OPEN_METEO", "IMD_PUNE"]),
                                                 DatasetRegistry.source.like("NCMRWF%")))
            .order_by(DatasetRegistry.ingestion_timestamp.desc()).limit(min(limit, 200)).all())
    return [{"dataset_id": r.dataset_id, "name": r.name, "badge": r.provenance_badge, "records": r.record_count,
             "checksum": r.checksum, "url": r.file_path, "variables": r.variables, "metadata": r.metadata_json,
             "ingested_at": r.ingestion_timestamp.isoformat() if r.ingestion_timestamp else None,
             "coverage": [r.temporal_coverage_start.isoformat() if r.temporal_coverage_start else None,
                          r.temporal_coverage_end.isoformat() if r.temporal_coverage_end else None]} for r in rows]
