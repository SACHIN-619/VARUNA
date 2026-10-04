"""
VARUNA Background Jobs API Router.
SIH 2026 Problem Statement: SIH26081

Handles asynchronous execution of heavy scientific workloads:
- Ingestion
- Benchmark evaluation
- Verification cycles
- ML model recalibration
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.auth import get_current_user, require_role, require_permission
from app.models.user import User
from app.services.job_queue import job_queue
from app.services.ingestion import ingestion_engine
from app.experiments.benchmark_runner import benchmark_runner
from app.intelligence.ml_trust_model import ml_trust_model
from app.services.data_pipeline import data_pipeline

from datetime import datetime, timezone

router = APIRouter(prefix="/jobs", tags=["Background Jobs & Pipeline Execution"])


class BenchmarkJobRequest(BaseModel):
    n_days: int = Field(500, ge=100, le=2000, description="Total days for benchmark generation")
    random_seed: int = Field(101, description="Deterministic seed for reproducibility")
    dataset_id: str = Field("SYNTHETIC_STRESS_TEST_MONSOON_2026", description="Dataset identifier")


class RecalibrateJobRequest(BaseModel):
    region_id: str = Field("IN_TELANGANA_HYDERABAD", description="Target region")
    variable: str = Field("rainfall", description="Target meteorological variable")
    lead_hours: int = Field(48, description="Lead hours")


class VerifyJobRequest(BaseModel):
    region_id: str = Field("IN_TELANGANA_HYDERABAD")
    variable: str = Field("rainfall")
    lead_hours: int = Field(48)
    ground_truth: Optional[float] = Field(None, description="Optional verified observation value")


@router.get("")
def list_all_jobs(limit: int = Query(50, le=200)):
    """Lists recent background pipeline jobs and their execution states."""
    return job_queue.list_jobs(limit=limit)


@router.get("/{job_id}")
def get_job_status(job_id: str):
    """Retrieves real-time progress and output of an asynchronous pipeline job."""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job.to_dict()


@router.post("/benchmark")
def launch_benchmark_job(
    req: BenchmarkJobRequest,
    _user: User = Depends(require_permission("experiment:run"))
):
    """Submits a reproducible benchmark experiment to the background worker."""
    def _run_bench():
        runner = benchmark_runner.__class__(
            n_days=req.n_days,
            random_seed=req.random_seed,
            dataset_id=req.dataset_id
        )
        return runner.run_experiment()

    job_id = job_queue.submit_job(
        job_type="benchmark",
        target_fn=_run_bench,
        metadata={"dataset_id": req.dataset_id, "n_days": req.n_days, "seed": req.random_seed}
    )
    return {"job_id": job_id, "status": "QUEUED", "message": "Benchmark experiment dispatched to background queue."}


@router.post("/recalibrate")
def launch_recalibration_job(
    req: RecalibrateJobRequest,
    _user: User = Depends(require_permission("skill:update"))
):
    """Submits a model skill update and meta-model recalibration job."""
    def _run_recalibration():
        db = SessionLocal()
        try:
            skill_res = data_pipeline.update_model_skills_from_history(
                db=db,
                region_id=req.region_id,
                variable=req.variable,
                lead_hours=req.lead_hours
            )
            # Retrain ML Meta-Model bootstrap
            ml_trust_model._train_default_bootstrap_model()
            return {
                "skill_update": skill_res,
                "ml_model_refreshed": True,
                "recalibrated_at": skill_res.get("timestamp")
            }
        finally:
            db.close()

    job_id = job_queue.submit_job(
        job_type="recalibrate",
        target_fn=_run_recalibration,
        metadata={"region_id": req.region_id, "variable": req.variable, "lead_hours": req.lead_hours}
    )
    return {"job_id": job_id, "status": "QUEUED", "message": "Model recalibration dispatched to background queue."}


@router.post("/verify")
def launch_verification_job(
    req: VerifyJobRequest,
    _user: User = Depends(require_permission("verification:run"))
):
    """Submits an operational verification cycle to the background queue."""
    def _run_verification():
        db = SessionLocal()
        try:
            return data_pipeline.ingest_and_verify_cycle(
                db=db,
                region_id=req.region_id,
                variable=req.variable,
                lead_hours=req.lead_hours,
                model_forecasts={"NCUM": 82.0, "GFS": 103.0, "WRF": 47.0, "AI_WEATHER": 64.0},
                fused_forecast=71.8,
                valid_time=datetime.now(timezone.utc),
                ground_truth=req.ground_truth
            )
        finally:
            db.close()

    job_id = job_queue.submit_job(
        job_type="verify",
        target_fn=_run_verification,
        metadata={"region_id": req.region_id, "variable": req.variable}
    )
    return {"job_id": job_id, "status": "QUEUED", "message": "Verification cycle dispatched to background queue."}


@router.post("/ingest")
async def launch_async_ingestion_job(
    dataset_id: str = Form(...),
    source: str = Form("NCMRWF"),
    provenance: str = Form("PUBLIC_BENCHMARK"),
    file: UploadFile = File(...),
    _user: User = Depends(require_permission("data:ingest"))
):
    """Submits a large dataset file for background chunked ingestion."""
    content = await file.read()
    fname = file.filename or "data.csv"

    def _run_ingest():
        db = SessionLocal()
        try:
            return ingestion_engine.ingest_dataset(
                db=db,
                dataset_id=dataset_id,
                file_content=content,
                filename=fname,
                source=source,
                provenance=provenance,
                persist_records=True
            )
        finally:
            db.close()

    job_id = job_queue.submit_job(
        job_type="ingest",
        target_fn=_run_ingest,
        metadata={"dataset_id": dataset_id, "filename": fname, "size_bytes": len(content)}
    )
    return {"job_id": job_id, "status": "QUEUED", "message": "Dataset ingestion dispatched to background queue."}


@router.post("/{job_id}/cancel")
def cancel_running_job(job_id: str, _user: User = Depends(get_current_user)):
    """Cancels a queued or running background job."""
    success = job_queue.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Job '{job_id}' cannot be cancelled (already completed or not found).")
    return {"job_id": job_id, "status": "CANCELLED"}
