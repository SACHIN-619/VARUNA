from typing import Dict, Any
from app.intelligence.failure_memory import failure_memory

def compute_model_reliability(
    model_id: str,
    historical_mae: float,
    recent_error: float,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes a dynamically adjusted reliability index for a forecast model,
    penalizing high historical error, recent error spikes, and known regime vulnerabilities.
    """
    # Inverse MAE baseline (lower MAE = higher base skill)
    base_skill = 1.0 / max(historical_mae, 1.0)
    
    # Recent error penalty
    recent_penalty = 1.0 / (1.0 + max(0.0, recent_error) / 15.0)
    
    # Failure memory & regime vulnerability multiplier
    regime = context.get("weather_regime", "NORMAL")
    lead_hours = context.get("lead_hours", 48)
    season = context.get("season", "SW_MONSOON")
    
    vuln = failure_memory.evaluate_historical_vulnerability(
        model_id=model_id,
        weather_regime=regime,
        lead_hours=lead_hours,
        season=season
    )
    
    # Total reliability score
    composite_reliability = base_skill * recent_penalty * vuln["vulnerability_multiplier"]
    
    return {
        "model_id": model_id,
        "base_skill": round(base_skill, 4),
        "recent_penalty": round(recent_penalty, 3),
        "vulnerability_multiplier": vuln["vulnerability_multiplier"],
        "composite_reliability": round(composite_reliability, 5),
        "notes": vuln["reasons"]
    }
