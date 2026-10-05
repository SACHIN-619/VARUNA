from typing import Optional, List
from app.core.auth import require_permission
from app.models.user import User
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.experiment import ExperimentRun
from app.verification.baselines import compare_fusion_baselines
from app.experiments.benchmark_runner import benchmark_runner
from app.services.data_pipeline import data_pipeline

router = APIRouter(prefix="/verification", tags=["Forecast Verification & Benchmarks"])

from functools import lru_cache


@lru_cache(maxsize=1)
def _benchmark_snapshot():
    """
    Single source of truth for verification numbers shown in the UI: the leak-free
    chronological benchmark (cached; ~0.5 s to compute once).
    Previously /summary and /compare used a hand-typed 10-row table whose "adaptive_blend"
    column was entered manually, reporting a 79% MAE reduction that contradicted the real
    benchmark (~1-10%). Those fabricated rows were removed.
    """
    from app.experiments.benchmark_runner import BenchmarkExperimentRunner
    return BenchmarkExperimentRunner(random_seed=101).run_experiment()


def _method_key(name: str) -> str:
    return {
        "ADAPTIVE_ML_META_MODEL": "ADAPTIVE_BLEND",
        "SIMPLE_AVERAGE": "SIMPLE_AVERAGE",
        "STATIC_BLEND": "STATIC_BLEND",
    }.get(name, name)


@router.get("/summary")
def get_verification_summary(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    variable: str = Query("rainfall"),
    lead_hours: int = Query(48)
):
    """High-level verification metrics from the chronological (held-out) benchmark."""
    res = _benchmark_snapshot()
    f = res["scientific_findings"]
    return {
        "region_id": region_id,
        "variable": variable,
        "lead_hours": lead_hours,
        "sample_size": f["test_sample_count"],
        "adaptive_advantage_mae_reduction_pct": f["ml_mae_reduction_vs_simple_average_pct"],
        "stacking_advantage_mae_reduction_pct": f.get("stacking_mae_reduction_vs_simple_average_pct"),
        "best_method": f.get("best_method"),
        "evaluation_window": f"{res['chronological_partitions']['test']['start'][:10]} to {res['chronological_partitions']['test']['end'][:10]}",
        "provenance": res["data_provenance"],
        "note": "Synthetic chronological benchmark (not operational verification). Variable-specific benchmarks exist for rainfall only.",
    }


@router.get("/compare")
def get_baseline_comparison(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    variable: str = Query("rainfall"),
    lead_hours: int = Query(48)
):
    """Individual models vs Simple Average vs Static Blend vs Adaptive (heuristic / ML) vs Bias-Corrected Stacking."""
    res = _benchmark_snapshot()
    f = res["scientific_findings"]
    by_method = {_method_key(m["method"]): {**m, "corr": m.get("correlation")} for m in res["results_table"]}
    return {
        "region_id": region_id,
        "variable": variable,
        "lead_hours": lead_hours,
        "evaluation_window": f"{res['chronological_partitions']['test']['start'][:10]} to {res['chronological_partitions']['test']['end'][:10]}",
        "sample_size": f["test_sample_count"],
        "methods": res["results_table"],
        "baselines": by_method,
        "adaptive_advantage_mae_reduction_pct": f["ml_mae_reduction_vs_simple_average_pct"],
        "stacking_advantage_mae_reduction_pct": f.get("stacking_mae_reduction_vs_simple_average_pct"),
        "best_method": f.get("best_method"),
        "data_provenance": res["data_provenance"]
    }

@router.get("/experiment")
def get_temporal_split_experiment(
    persist: bool = Query(False, description="Persist this experiment run to database"),
    db: Session = Depends(get_db)
):
    """
    Rigorous scientific benchmark evaluating 5 paradigms on a strictly unseen chronological test set:
    1. Individual Models (NCUM, GFS, WRF, AI)
    2. Simple Multi-Model Average
    3. Static Operational Blend
    4. Adaptive Reliability Baseline (Heuristic Formula)
    5. Adaptive ML Meta-Model (Learned Gradient Boosting + Softmax Gating)
    
    Guarantees: Zero temporal data leakage (70% train / 30% unseen future test).
    Optionally persists the benchmark run to PostgreSQL / Neon.
    """
    res = benchmark_runner.run_experiment()
    
    if persist:
        run_record = ExperimentRun(
            title=res["title"],
            split_ratio=benchmark_runner.split_ratio,
            train_samples=res["train_samples"],
            unseen_test_samples=res["unseen_test_samples"],
            variable="rainfall",
            provenance=res["data_provenance"],
            results_table=res["results_table"],
            mae_reduction_vs_simple_avg_pct=res["scientific_findings"]["ml_mae_reduction_vs_simple_average_pct"],
            mae_reduction_vs_heuristic_pct=res["scientific_findings"]["ml_mae_reduction_vs_heuristic_baseline_pct"],
            scientific_summary=res["scientific_findings"],
            markdown_report=res.get("markdown_report")
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)
        res["persisted_id"] = run_record.id

    return res

@router.get("/experiments")
def list_saved_experiments(
    limit: int = Query(20, description="Max runs to return"),
    db: Session = Depends(get_db)
):
    """Lists saved empirical experiment runs from database."""
    runs = db.query(ExperimentRun).order_by(ExperimentRun.executed_at.desc()).limit(limit).all()
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

@router.get("/experiments/{experiment_id}")
def get_saved_experiment(experiment_id: str, db: Session = Depends(get_db)):
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

@router.get("/experiments/{experiment_id}/report", response_class=PlainTextResponse)
def get_experiment_report(experiment_id: str, db: Session = Depends(get_db)):
    """Exports the complete reproducible scientific markdown report for an experiment."""
    run = db.query(ExperimentRun).filter(ExperimentRun.id == experiment_id).first()
    if not run or not run.markdown_report:
        # Fallback to generating live report if not found in db
        res = benchmark_runner.run_experiment()
        return res["markdown_report"]
    return run.markdown_report

@router.post("/feedback-loop")
def trigger_closed_loop_skill_update(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    variable: str = Query("rainfall"),
    lead_hours: int = Query(48),
    season: str = Query("SW_MONSOON"),
    weather_regime: str = Query("HEAVY_RAINFALL"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("skill:update"))
):
    from app.services.audit_service import record as _audit
    """
    Executes the closed-loop scientific feedback mechanism:
    Aggregates verification records, updates model skill scores in database,
    and updates adaptive reliability parameters for subsequent forecast cycles.
    """
    res = data_pipeline.update_model_skills_from_history(
        db=db,
        region_id=region_id,
        variable=variable,
        lead_hours=lead_hours,
        season=season,
        weather_regime=weather_regime
    )
    _audit(db, "SKILL_UPDATE", "MODEL_SKILL", f"{region_id}/{variable}/{lead_hours}h", actor=_user,
           metadata={"season": season, "weather_regime": weather_regime})
    return res


from pydantic import BaseModel as _BM, Field as _F  # noqa: E402
from fastapi import Request  # noqa: E402


class VerifyRunRequest(_BM):
    region_id: str = "IN_TELANGANA_HYDERABAD"
    variable: str = "rainfall"
    lead_hours: int = 48
    season: str = "SW_MONSOON"
    weather_regime: str = "HEAVY_RAINFALL"
    strategy: Optional[str] = None
    source: str = "auto"
    observed_value: Optional[float] = _F(None, description="Manual observation (e.g. gauge reading) in canonical units")
    observation_source: str = _F("MANUAL_ENTRY", description="Free text: station id / gauge / IMD bulletin reference")
    use_era5: bool = _F(False, description="Look up ERA5 for the valid day (global fallback, ~5-6 day latency)")
    use_imd: bool = _F(False, description="Look up IMD gridded observation for the valid day (rainfall/Tmax, ~1-2 day lag)")
    valid_date: Optional[str] = _F(None, description="YYYY-MM-DD; defaults to the forecast's valid day")


@router.post("/verify-run")
def verify_run(req: VerifyRunRequest, request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_permission("verification:run"))):
    """
    Stage 14 on demand: re-run the current forecast, compare every model and the fused value with an observation,
    and store the errors as verification records. Skill memory is then updated with POST /verification/feedback-loop
    (skill:update) or an approved RECALIBRATE_SKILL proposal.
    """
    from datetime import date as _date, timedelta as _td
    from app.api.dashboard import resolve_package
    from app.services.canonical_pipeline import canonical_pipeline
    from app.services.audit_service import record as audit

    pkg, source_mode, _note = resolve_package(db, req.region_id, req.variable, req.lead_hours, req.weather_regime,
                                              req.season, req.strategy or "ADAPTIVE_ML", None, req.source)
    valid_day = req.valid_date or (pkg.get("inputs", {}).get("source_meta") or {}).get(
        next(iter(pkg.get("models") or []), ""), {}).get("valid_time", "")[:10] or (
        _date.today() + _td(hours=req.lead_hours)).isoformat()
    obs, obs_src = req.observed_value, req.observation_source
    if obs is None and req.use_imd:
        from app.services import india_sources as ind
        from app.services import live_sources as ls
        d = _date.fromisoformat(valid_day[:10])
        ready = _date.today() - _td(days=ind.IMD_REALTIME_LAG_DAYS)
        if d > ready:
            return {"status": "AWAITING_OBSERVATION", "valid_day": valid_day,
                    "reference_available_after": (d + _td(days=ind.IMD_REALTIME_LAG_DAYS)).isoformat(),
                    "message": f"IMD gridded data for {valid_day} is published ~{ind.IMD_REALTIME_LAG_DAYS} days later. "
                               "Enter a gauge/AWS observation now or retry after the date shown."}
        try:
            region = ls.resolve_region(db, req.region_id)
            imd = ind.fetch_imd_truth(region, req.variable, d, d)
        except (ind.IndiaSourceError, ls.LiveSourceError) as exc:
            raise HTTPException(502, f"IMD gridded lookup failed: {exc}")
        obs = imd["truth"].get(d.isoformat())
        cell = next(iter(imd["cells"].values()), {})
        obs_src = f"IMD gridded ({', '.join(imd['files'])}; cell {cell.get('cell_lat')},{cell.get('cell_lon')})"
        if obs is None:
            return {"status": "AWAITING_OBSERVATION", "valid_day": valid_day, "message": "IMD grid has no value at this location."}
    if obs is None and req.use_era5:
        from app.services import live_sources as ls
        d = _date.fromisoformat(valid_day[:10])
        ready = _date.today() - _td(days=ls.ERA5_LATENCY_DAYS)
        if d > ready:
            return {"status": "AWAITING_OBSERVATION", "valid_day": valid_day,
                    "reference_available_after": (d + _td(days=ls.ERA5_LATENCY_DAYS)).isoformat(),
                    "message": f"ERA5 for {valid_day} is not published yet (~{ls.ERA5_LATENCY_DAYS} day latency). "
                               "Enter a manual observation or retry after the date shown."}
        try:
            region = ls.resolve_region(db, req.region_id)
            era = ls.fetch_era5(region, req.variable, d, d)
        except ls.LiveSourceError as exc:
            raise HTTPException(502, f"ERA5 lookup failed: {exc}")
        obs = era["truth"].get(d.isoformat())
        obs_src = f"ERA5 via Open-Meteo ({era['url']})"
        if obs is None:
            return {"status": "AWAITING_OBSERVATION", "valid_day": valid_day, "message": "ERA5 returned no value."}
    if obs is None:
        raise HTTPException(422, "Provide observed_value or set use_imd / use_era5.")

    forecasts = {m: v for m, v in pkg["inputs"]["harmonized_forecasts"].items() if v is not None}
    fused = pkg["fusion"].get("fused_value")
    result = canonical_pipeline.verify_and_update_skill(
        db=db, region_id=pkg["region_id"], variable=req.variable, lead_hours=req.lead_hours,
        model_forecasts=forecasts, fused_forecast=fused, observation_val=float(obs))
    result.update({"valid_day": valid_day, "observation_source": obs_src, "source_mode": source_mode,
                   "run_id": pkg.get("run_id"), "fused_forecast": fused,
                   "next_step": "Update skill memory (POST /api/verification/feedback-loop) to fold these errors into model skill."})
    audit(db, "VERIFY_RUN", "FORECAST_RUN", pkg.get("run_id"), actor=user,
          metadata={"region_id": pkg["region_id"], "variable": req.variable, "lead_hours": req.lead_hours,
                    "observed": obs, "observation_source": obs_src, "source_mode": source_mode},
          request_ip=request.client.host if request.client else None)
    return result


@router.get("/live-skill")
def live_skill(region_id: str = Query("IN_TELANGANA_HYDERABAD"), variable: str = Query("rainfall"),
               db: Session = Depends(get_db)):
    """
    Verified skill of the public models for one region, from the ERA5 backfill (real data, small samples).
    Empty `leads` means no backfill has been run for this region/variable yet.
    """
    from app.models.skill import ModelSkill
    from app.services.harmonization import normalize_region_id
    from app.services.live_sources import BACKFILL_PERIODS
    rid = normalize_region_id(region_id)
    rows = db.query(ModelSkill).filter(ModelSkill.region_id == rid, ModelSkill.variable == variable,
                                       ModelSkill.evaluation_period.in_(BACKFILL_PERIODS)).all()
    leads: dict = {}
    updated = None
    periods = set()
    for r in rows:
        periods.add(r.evaluation_period)
        leads.setdefault(str(r.lead_hours), {}).setdefault(r.model_id, {})[r.metric] = r.value
        leads[str(r.lead_hours)][r.model_id]["n"] = r.sample_count
        if r.updated_at and (updated is None or r.updated_at > updated):
            updated = r.updated_at
    ref = ("IMD gridded observations (IMD Pune)" if periods == {"LIVE_BACKFILL_IMD"} else
           "ERA5 reanalysis (not station observations)" if periods == {"LIVE_BACKFILL_ERA5"} else
           "IMD gridded + ERA5 (mixed)" if periods else None)
    return {"region_id": rid, "variable": variable, "evaluation_period": sorted(periods),
            "reference": ref, "leads": leads,
            "updated_at": updated.isoformat() if updated else None}


@router.get("/records")
def verification_records(region_id: str = Query("IN_TELANGANA_HYDERABAD"), variable: str = Query("rainfall"),
                         limit: int = Query(50, le=500), db: Session = Depends(get_db)):
    """Most recent stored verification rows (forecast, observation, |error|, window) for traceability."""
    from app.models.verification import VerificationResult
    from app.services.harmonization import normalize_region_id
    rid = normalize_region_id(region_id)
    rows = (db.query(VerificationResult)
            .filter(VerificationResult.region_id == rid, VerificationResult.variable == variable,
                    VerificationResult.metric == "MAE")
            .order_by(VerificationResult.verification_time.desc()).limit(limit).all())
    return [{"model_id": r.model_id or "VARUNA_FUSED", "method": r.method, "lead_hours": r.lead_hours,
             "forecast": r.forecast_value, "observed": r.observed_value, "abs_error": r.score,
             "window": r.evaluation_window,
             "time": r.verification_time.isoformat() if r.verification_time else None} for r in rows]


@router.get("/drift")
def trust_drift(variable: str = Query("rainfall"), region_id: Optional[str] = Query(None),
                recent: int = Query(7, ge=3, le=60, description="Most recent verified cases compared with the rest"),
                min_baseline: int = Query(7, ge=3, le=365),
                ratio_threshold: float = Query(1.5, gt=1.0, le=5.0),
                db: Session = Depends(get_db)):
    """
    Trust drift from stored verification history (nothing simulated).

    For every model × region × lead time: baseline MAE (older cases) vs recent MAE (last `recent` cases, by valid
    time). DEGRADING when recent ≥ ratio_threshold × baseline and the gap exceeds a unit floor; IMPROVING when
    recent ≤ baseline / ratio_threshold; otherwise STABLE. Too few cases → INSUFFICIENT_HISTORY.
    Drift is a flag for review; it never removes a model by itself.
    """
    from app.models.verification import VerificationResult
    from app.services.harmonization import normalize_region_id
    floor = {"rainfall": 2.0, "temperature": 0.5, "wind_speed": 0.5}.get(variable, 1.0)
    q = db.query(VerificationResult).filter(VerificationResult.variable == variable,
                                            VerificationResult.metric == "MAE",
                                            VerificationResult.model_id.isnot(None))
    if region_id:
        q = q.filter(VerificationResult.region_id == normalize_region_id(region_id))
    groups: dict = {}
    for r in q.order_by(VerificationResult.verification_time.asc()).all():
        groups.setdefault((r.region_id, r.model_id, r.lead_hours), []).append(r)

    items = []
    for (rid, mid, lead), rows in groups.items():
        errs = [abs(r.score) for r in rows]
        biases = [(r.forecast_value - r.observed_value) for r in rows
                  if r.forecast_value is not None and r.observed_value is not None]
        n = len(errs)
        item = {"region_id": rid, "model_id": mid, "lead_hours": lead, "n": n,
                "errors": [round(e, 2) for e in errs[-60:]],
                "references": sorted({r.evaluation_window for r in rows if r.evaluation_window}),
                "first_valid": rows[0].verification_time.isoformat() if rows[0].verification_time else None,
                "last_valid": rows[-1].verification_time.isoformat() if rows[-1].verification_time else None}
        if n < recent + min_baseline:
            item.update({"status": "INSUFFICIENT_HISTORY", "baseline_mae": None, "recent_mae": None, "ratio": None,
                         "recent_bias": None, "needed": recent + min_baseline})
        else:
            base = sum(errs[:-recent]) / (n - recent)
            rec = sum(errs[-recent:]) / recent
            rb = biases[-recent:]
            ratio = rec / max(base, floor)
            if ratio >= ratio_threshold and rec - base >= floor:
                status = "DEGRADING"
            elif ratio <= 1 / ratio_threshold and base - rec >= floor:
                status = "IMPROVING"
            else:
                status = "STABLE"
            item.update({"status": status, "baseline_mae": round(base, 2), "recent_mae": round(rec, 2),
                         "ratio": round(ratio, 2), "recent_bias": round(sum(rb) / len(rb), 2) if rb else None})
        items.append(item)
    order = {"DEGRADING": 0, "IMPROVING": 1, "STABLE": 2, "INSUFFICIENT_HISTORY": 3}
    items.sort(key=lambda i: (order[i["status"]], -(i["ratio"] or 0), i["region_id"], i["model_id"]))
    return {"variable": variable, "rule": {"recent": recent, "min_baseline": min_baseline,
                                           "ratio_threshold": ratio_threshold, "unit_floor": floor},
            "counts": {s: sum(1 for i in items if i["status"] == s) for s in order}, "items": items}
