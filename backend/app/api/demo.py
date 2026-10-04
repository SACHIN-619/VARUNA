from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.auth import require_permission
from app.core.database import get_db
from app.models.user import User
from app.services.audit_service import record as audit
from app.demo.scenario_generator import scenario_generator
from app.intelligence.failure_memory import failure_memory
from app.schemas.all_schemas import FailureInjectionRequest

router = APIRouter(prefix="/demo", tags=["Demo Scenarios & Failure Injection"])

@router.get("/scenarios")
def list_scenarios():
    """Lists available reproducible demonstration scenarios."""
    return scenario_generator.list_scenarios()

@router.post("/load-scenario/{scenario_id}")
def load_scenario(scenario_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("demo:inject"))):
    """Loads a specific scenario and resets previous runtime failure overrides."""
    failure_memory.reset()
    success = scenario_generator.set_active_scenario(scenario_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    return {
        "status": "LOADED",
        "active_scenario_id": scenario_id,
        "details": scenario_generator.get_scenario(scenario_id)
    }

@router.post("/inject-failure")
def inject_failure(req: FailureInjectionRequest, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("demo:inject"))):
    """
    Simulates operational failure modes:
    - simulate_model_bias: GFS or target model develops large error drift
    - simulate_missing_model: Deactivates target model (e.g. NCUM) triggering weight re-normalization
    - simulate_disagreement: Drastically widens model spread
    - reset_scenario: Clears all failure overrides
    """
    action = req.action.lower().strip()
    target_model = req.model_id.upper() if req.model_id else "GFS"

    if action == "simulate_model_bias":
        bias = req.bias_magnitude or 35.0
        failure_memory.inject_model_bias(target_model, bias)
        msg = f"Injected operational bias (+{bias} mm) into {target_model}. Recent error increased."
    elif action == "simulate_missing_model":
        failure_memory.disable_model(target_model)
        msg = f"Model {target_model} marked UNAVAILABLE. Remaining weights re-normalized."
    elif action == "simulate_disagreement":
        failure_memory.force_disagreement(True)
        msg = "Forced multi-model divergence. Epistemic uncertainty increased; confidence lowered."
    elif action == "reset_scenario":
        failure_memory.reset()
        msg = "All failure overrides cleared. Nominal operational state restored."
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action '{req.action}'.")

    # Simulation changes shared demo state for every viewer: always authenticated and audited
    audit(db, "DEMO_INJECT", "DEMO_SCENARIO", target_model, actor=user, metadata={"action": action, "message": msg})
    # Re-evaluate pipeline to immediately return the impact
    state = scenario_generator.execute_pipeline()
    return {
        "action": action,
        "message": msg,
        "affected_model": target_model if action != "reset_scenario" else None,
        "active_overrides": {
            "injected_bias": failure_memory._injected_bias,
            "disabled_models": list(failure_memory._disabled_models),
            "forced_disagreement": failure_memory.is_forced_disagreement()
        },
        "updated_fused_value": state["fused_value"],
        "updated_confidence": state["uncertainty"]["confidence"],
        "updated_disagreement": state["disagreement"]["disagreement_level"],
        "updated_weights": state["weights"]
    }

@router.get("/status")
def get_failure_injection_status():
    """Returns current active failure injection overrides."""
    return {
        "active_scenario_id": scenario_generator.current_scenario_id,
        "injected_bias": failure_memory._injected_bias,
        "disabled_models": list(failure_memory._disabled_models),
        "forced_disagreement": failure_memory.is_forced_disagreement()
    }
