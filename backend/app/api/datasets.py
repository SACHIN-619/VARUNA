"""
VARUNA Dataset Registry & Ingestion API Router.
SIH 2026 Problem Statement: SIH26081
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.dataset_registry import dataset_registry_service
from app.services.ingestion import ingestion_engine
from app.models.canonical_record import CanonicalWeatherEntity
from app.core.auth import require_permission
from app.models.user import User

router = APIRouter(prefix="/datasets", tags=["Dataset Registry & Ingestion"])

@router.get("")
def list_datasets(
    status: Optional[str] = Query(None, description="Filter by status e.g. AVAILABLE | INGESTING | AUTHORIZED_PROVIDER_REQUIRED"),
    provenance: Optional[str] = Query(None, description="Filter by provenance e.g. PUBLIC_BENCHMARK | SYNTHETIC_STRESS_TEST | AUTHORIZED_OPERATIONAL_FEED"),
    db: Session = Depends(get_db)
):
    """Lists all registered meteorological datasets in the VARUNA catalog."""
    return dataset_registry_service.list_datasets(db, status=status, provenance=provenance)


@router.get("/{dataset_id}")
def get_dataset_details(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieves full specification, checksum, resolution, and availability for a dataset."""
    ds = dataset_registry_service.get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found in registry.")
    return ds


@router.get("/{dataset_id}/records")
def get_dataset_records(
    dataset_id: str,
    region_id: Optional[str] = Query(None),
    variable: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Paginated access to normalized canonical records for large-scale data queries.
    Prevents unbounded in-memory query explosions.
    """
    query = db.query(CanonicalWeatherEntity).filter(CanonicalWeatherEntity.dataset_id == dataset_id)
    if region_id:
        query = query.filter(CanonicalWeatherEntity.region_id == region_id)
    if variable:
        query = query.filter(CanonicalWeatherEntity.variable == variable)

    total = query.count()
    records = query.order_by(CanonicalWeatherEntity.valid_time.desc()).offset(offset).limit(limit).all()

    return {
        "dataset_id": dataset_id,
        "total_records": total,
        "limit": limit,
        "offset": offset,
        "records": [
            {
                "id": r.id,
                "model_id": r.model_id,
                "region_id": r.region_id,
                "variable": r.variable,
                "lead_time": r.lead_time,
                "value": r.value,
                "unit": r.unit,
                "valid_time": r.valid_time.isoformat(),
                "quality_flag": r.quality_flag,
                "provenance": r.provenance
            }
            for r in records
        ]
    }


@router.post("/ingest")
def ingest_dataset_file(
    dataset_id: Optional[str] = Form(None, description="Unique dataset identifier e.g. IMDAA_OBS_BATCH_2026"),
    source: str = Form("NCMRWF / IMD"),
    version: str = Form("v1.0"),
    provenance: str = Form("PUBLIC_BENCHMARK", description="PUBLIC_BENCHMARK | SYNTHETIC_STRESS_TEST | AUTHORIZED_OPERATIONAL_FEED"),
    file: UploadFile = File(..., description="Meteorological data file (CSV, JSON, JSONL, Parquet, GeoJSON, ZIP)"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("data:ingest"))
):
    """
    Streams, validates, normalizes, and ingests heterogeneous meteorological datasets.
    Operates in bounded memory chunks (DATA_CHUNK_SIZE=10000).
    """
    # Sync endpoint -> runs in FastAPI's threadpool, so a large CPU/DB-bound ingestion
    # no longer blocks the event loop for every other request (it was `async def`).
    # Max file upload size limit: 100MB for standard API upload
    content = file.file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum supported HTTP upload size is 100MB.")

    if not dataset_id:
        import uuid
        dataset_id = f"DS_INGEST_{uuid.uuid4().hex[:8].upper()}"

    try:
        res = ingestion_engine.ingest_dataset(
            db=db,
            dataset_id=dataset_id,
            file_content=content,
            filename=file.filename or "upload.csv",
            source=source,
            version=version,
            provenance=provenance,
            persist_records=True
        )
    except Exception as e:
        from app.services.audit_service import record as audit
        audit(db, "DATA_INGEST", "DATASET", dataset_id, actor=_user, result="FAILED", reason=str(e)[:500],
              metadata={"filename": file.filename, "provenance": provenance, "bytes": len(content)})
        raise HTTPException(status_code=400, detail=str(e))
    import hashlib
    from app.services.audit_service import record as audit
    audit(db, "DATA_INGEST", "DATASET", dataset_id, actor=_user,
          metadata={"filename": file.filename, "source": source, "provenance": provenance, "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "records": (res or {}).get("records_ingested") or (res or {}).get("record_count")})
    return res
