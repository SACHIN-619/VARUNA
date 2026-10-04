"""
VARUNA Reproducible Experiment Execution & Audit API Router.
SIH 2026 Problem Statement: SIH26081

Endpoints:
- POST /api/experiments/run: Executes a reproducible benchmark run with specific seeds, datasets, and splits
- GET /api/experiments: Lists all historical experiment audits
- GET /api/experiments/{experiment_id}: Retrieves full parameters, seeds, partitions, and metrics
- GET /api/experiments/{experiment_id}/report: Exports Markdown scientific verification report
"""

from typing import Optional, Dict, Any
from app.core.auth import require_permission
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.experiment import ExperimentRun
from app.experiments.benchmark_runner import BenchmarkExperimentRunner
from app.schemas.canonical import DataProvenance

router = APIRouter(prefix="/experiments", tags=["Reproducible Scientific Experiments"])


class RunExperimentRequest(BaseModel):
    title: Optional[str] = Field(None, description="Custom experiment title")
    lane: str = Field("demo", description="Lane selection: 'demo' (synthetic stress test) or 'research' (real open meteorological dataset)")
    dataset_id: str = Field("SYNTHETIC_STRESS_TEST_MONSOON_2026", description="Target dataset")
    dataset_version: str = Field("v2026.1")
    provenance: str = Field(DataProvenance.SYNTHETIC_STRESS_TEST.value, description="Data provenance badge")
    random_seed: int = Field(101, description="Deterministic seed for exact reproducibility")
    n_days: int = Field(500, ge=100, le=2000, description="Total chronological days")
    train_ratio: float = Field(0.60, ge=0.4, le=0.8)
    val_ratio: float = Field(0.15, ge=0.05, le=0.3)
    persist: bool = Field(True, description="Persist experiment results to database")



@router.post("/run")
def execute_reproducible_experiment(
    req: RunExperimentRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("experiment:run"))
):
    """
    Executes a reproducible, leak-free benchmark comparing all 5 paradigms.
    Stores complete code versions, random seeds, and chronological partitions.
    """
    runner = BenchmarkExperimentRunner(
        n_days=req.n_days,
        train_ratio=req.train_ratio,
        val_ratio=req.val_ratio,
        random_seed=req.random_seed,
        provenance=req.provenance,
        dataset_id=req.dataset_id,
        lane=req.lane
    )


    res = runner.run_experiment(custom_seed=req.random_seed)

    if req.persist:
        run_record = ExperimentRun(
            id=res["experiment_id"],
            title=req.title or res["title"],
            split_ratio=round(req.train_ratio + req.val_ratio, 2),
            train_samples=res["chronological_partitions"]["train"]["samples"],
            unseen_test_samples=res["chronological_partitions"]["test"]["samples"],
            variable="rainfall",
            provenance=res["provenance_badge"],
            results_table=res["results_table"],
            mae_reduction_vs_simple_avg_pct=res["scientific_findings"]["ml_mae_reduction_vs_simple_average_pct"],
            mae_reduction_vs_heuristic_pct=res["scientific_findings"]["ml_mae_reduction_vs_heuristic_baseline_pct"],
            scientific_summary={
                "dataset_id": req.dataset_id,
                "dataset_version": req.dataset_version,
                "code_version": res["code_version"],
                "random_seed": req.random_seed,
                "chronological_partitions": res["chronological_partitions"],
                "findings": res["scientific_findings"]
            },
            markdown_report=res.get("markdown_report")
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)
    from app.services.audit_service import record as audit
    audit(db, "EXPERIMENT_RUN", "EXPERIMENT", getattr(locals().get("run_record"), "id", None), actor=_user)
    return res


@router.get("")
def list_experiments(
    limit: int = Query(25, le=100),
    provenance: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Lists saved empirical experiment runs from database."""
    query = db.query(ExperimentRun)
    if provenance:
        query = query.filter(ExperimentRun.provenance == provenance.upper())
    runs = query.order_by(ExperimentRun.executed_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "title": r.title,
            "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            "variable": r.variable,
            "train_samples": r.train_samples,
            "unseen_test_samples": r.unseen_test_samples,
            "mae_reduction_vs_simple_avg_pct": r.mae_reduction_vs_simple_avg_pct,
            "mae_reduction_vs_heuristic_pct": r.mae_reduction_vs_heuristic_pct,
            "provenance": r.provenance
        }
        for r in runs
    ]


@router.get("/{experiment_id}")
def get_experiment_by_id(experiment_id: str, db: Session = Depends(get_db)):
    """Retrieves full details of a saved empirical benchmark run."""
    run = db.query(ExperimentRun).filter(ExperimentRun.id == experiment_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    return {
        "id": run.id,
        "title": run.title,
        "executed_at": run.executed_at.isoformat() if run.executed_at else None,
        "split_ratio": run.split_ratio,
        "train_samples": run.train_samples,
        "unseen_test_samples": run.unseen_test_samples,
        "variable": run.variable,
        "provenance": run.provenance,
        "results_table": run.results_table,
        "mae_reduction_vs_simple_avg_pct": run.mae_reduction_vs_simple_avg_pct,
        "mae_reduction_vs_heuristic_pct": run.mae_reduction_vs_heuristic_pct,
        "scientific_summary": run.scientific_summary,
        "has_markdown_report": run.markdown_report is not None
    }


@router.get("/{experiment_id}/report", response_class=PlainTextResponse)
def get_experiment_markdown_report(experiment_id: str, db: Session = Depends(get_db)):
    """Exports the complete reproducible scientific markdown report for an experiment."""
    run = db.query(ExperimentRun).filter(ExperimentRun.id == experiment_id).first()
    if not run or not run.markdown_report:
        raise HTTPException(status_code=404, detail=f"Markdown report for '{experiment_id}' not found.")
    return run.markdown_report
