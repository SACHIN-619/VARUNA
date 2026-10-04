from datetime import datetime, timezone
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.demo.scenario_generator import scenario_generator

router = APIRouter(prefix="/dashboard", tags=["Dashboard Summary"])
logger = logging.getLogger("varuna.dashboard")

UNITS = {"rainfall": "mm", "temperature": "°C", "wind_speed": "m/s"}


def _latest_cycle_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0 if now.hour < 12 else 12, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_package(db: Session, region_id: str, variable: str, lead_hours: int, weather_regime: str, season: str,
                    strategy: str, disabled_model: Optional[str], source: str):
    """
    source = auto     -> India-first merge of fresh (<36 h) NCMRWF/IMD files + global public models, else the demo
             live     -> global public-model data only
             database -> latest stored issue of any provenance (e.g. your ingested files)
             demo     -> synthetic demo scenario
    Returns (package, source_mode, note).
    """
    from app.services.forecast_run_service import forecast_run_service
    from app.services.harmonization import normalize_region_id
    rid = normalize_region_id(region_id)
    source = (source or "auto").lower()
    note = ""
    if source == "auto" and db is not None:
        # India-first: authorised Indian feeds (NCMRWF / IMD files) + global public models, freshest per model
        pkg = forecast_run_service.run_from_database(db, rid, variable, lead_hours, season, weather_regime, strategy,
                                                     disabled_model=disabled_model, merge_fresh=True)
        if pkg is not None:
            mode = {"PUBLIC_API_FORECAST": "LIVE_PUBLIC_MODELS", "INDIA_OPERATIONAL": "INDIA_OPERATIONAL"}.get(
                pkg["data_type"], "INDIA_OPERATIONAL_PLUS_GLOBAL")
            return pkg, mode, ""
        note = ("No fresh forecasts stored for this region/variable/lead (NCMRWF/IMD files or live fetch) - "
                "showing the synthetic demo. Operations: Data sources → Fetch / NCMRWF scan.")
    if source == "live" and db is not None:
        pkg = forecast_run_service.run_from_database(db, rid, variable, lead_hours, season, weather_regime, strategy,
                                                     provenance="PUBLIC_API_FORECAST", disabled_model=disabled_model)
        if pkg is not None:
            return pkg, "LIVE_PUBLIC_MODELS", ""
        note = "No live fetch stored for this region/variable/lead yet - showing the synthetic demo."
    if source == "database" and db is not None:
        pkg = forecast_run_service.run_from_database(db, rid, variable, lead_hours, season, weather_regime, strategy,
                                                     disabled_model=disabled_model)
        if pkg is not None:
            return pkg, "STORED_DATA", ""
        note = "No stored records for this region/variable/lead - showing the synthetic demo."
    pkg = scenario_generator.execute_pipeline(custom_context={
        "region_id": region_id, "variable": variable, "lead_hours": lead_hours, "weather_regime": weather_regime,
        "season": season, "strategy": strategy, "disabled_model": disabled_model})
    return pkg, "SYNTHETIC_DEMO", note


@router.get("/summary")
def get_dashboard_summary(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    variable: str = Query("rainfall"),
    lead_hours: int = Query(48),
    weather_regime: str = Query("HEAVY_RAINFALL"),
    season: str = Query("SW_MONSOON"),
    strategy: Optional[str] = Query(None, description="ADAPTIVE_ML | ADAPTIVE_RELIABILITY | BIAS_CORRECTED_STACK (default: system config)"),
    disabled_model: Optional[str] = Query(None, description="Simulate a single model dropout for this request"),
    source: str = Query("auto", description="auto | live | database | demo"),
    db: Session = Depends(get_db),
):
    """
    Everything the control room needs, from one pipeline run. `source_mode` says honestly where the model
    values came from (SYNTHETIC_DEMO, LIVE_PUBLIC_MODELS or STORED_DATA); `stage_trace` and `lineage`
    explain every stage and every headline number.
    """
    if not strategy:
        try:
            from app.api.governance import get_config
            strategy = get_config(db)["default_strategy"]
        except Exception:
            strategy = "ADAPTIVE_ML"
    res, source_mode, note = resolve_package(db, region_id, variable, lead_hours, weather_regime, season, strategy,
                                             disabled_model, source)
    notification_id = None
    if not disabled_model:  # per-request dropout is a what-if, not a forecast change
        try:
            from app.services.notification_service import record_snapshot
            mode = {"SYNTHETIC_DEMO": "DEMO", "LIVE_PUBLIC_MODELS": "LIVE_PUBLIC"}.get(source_mode, source_mode)
            n = record_snapshot(db, res, mode)
            notification_id = n.id if n is not None else None
        except Exception as exc:  # notifications must never break the dashboard
            logger.warning("snapshot failed: %s", exc)
            try:
                db.rollback()
            except Exception:
                pass

    return {
        "active_cycle": res.get("issue_time") or _latest_cycle_iso(),
        "issue_time": res.get("issue_time"),
        "computed_at": res.get("timestamp"),
        "run_id": res.get("run_id"),
        "region_id": res["region_id"],
        "variable": res["variable"],
        "lead_hours": res["lead_hours"],
        "weather_regime": res["weather_regime"],
        "season": res["season"],
        "fused_forecast": res["fused_value"],
        "fused_value": res["fused_value"],
        "confidence_score": res.get("confidence_score", 0.0),
        "unit": UNITS.get(variable, ""),
        "baselines": res["baselines"],
        "model_forecasts": res["model_forecasts"],
        "models": res.get("models"),
        "weights": res["weights"],
        "disagreement": res["disagreement"],
        "uncertainty": res["uncertainty"],
        "extreme_guidance": res["extreme_guidance"],
        "explanation": res["explanation"],
        "what_changed": res["what_changed"],
        "data_health": res["data_health"],
        "provenance": res.get("data_type"),
        "data_mode": "LIVE",          # backend reachable (the UI switches to OFFLINE DEMO when it is not)
        "source_mode": source_mode,   # where the model values came from
        "source_note": note,
        "source_meta": res.get("inputs", {}).get("source_meta") or {},
        "qc_state": res.get("inputs", {}).get("qc_state") or {},
        "qc_flags": res.get("inputs", {}).get("qc_flags") or {},
        "dataset_ids": res.get("dataset_ids", []),
        "strategy": res.get("strategy", strategy),
        "strategy_note": res.get("strategy_note"),
        "skill_provenance": res.get("historical_skill", {}).get("provenance"),
        "pipeline_stages": res.get("provenance", {}).get("stages_executed"),
        "stage_trace": res.get("stage_trace", []),
        "lineage": res.get("lineage", {}),
        "notification_id": notification_id,
    }
