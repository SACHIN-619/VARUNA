from typing import Dict, List, Any
from datetime import datetime, timezone
from app.services.llm_provider import llm_service

def generate_forecast_explanation(
    fused_value: float,
    weights: List[Dict[str, Any]],
    disagreement_info: Dict[str, Any],
    uncertainty_info: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generates explainable AI (XAI) factors grounded directly in computed verification
    metrics, synoptic regime suitability, and model spread.
    """
    variable = context.get("variable", "rainfall")
    regime = context.get("weather_regime", "NORMAL")
    lead_hours = context.get("lead_hours", 48)

    # Identify dominant model
    active_weights = [w for w in weights if w.get("status") == "ACTIVE"]
    dominant = max(active_weights, key=lambda x: x["weight"]) if active_weights else None
    dominant_id = dominant["model_id"] if dominant else "NONE"
    dominant_pct = round(dominant["weight"] * 100.0, 1) if dominant else 0.0

    positive_factors = []
    negative_factors = []

    # Explain weights from the evidence actually used (no model-specific boilerplate)
    evidence = context.get("skill_provenance", {}) or {}
    skills = context.get("historical_skills", {}) or {}
    label = {
        "DATABASE_VERIFIED_HISTORY": "verified error history for this region",
        "SEEDED_PRIOR": "a seeded prior (not yet verified here)",
        "BOOTSTRAP_PRIOR": "a bootstrap prior (no verified history)",
        "SCENARIO_PRIOR": "the synthetic scenario's prior",
    }
    for w in sorted(weights, key=lambda x: -x.get("weight", 0)):
        m_id = w["model_id"]
        pct = round(w["weight"] * 100.0, 1)
        mae = (skills.get(m_id) or {}).get("MAE")
        ev = label.get(evidence.get(m_id), "its prior skill estimate")
        if w.get("status") in ("EXCLUDED", "DISABLED") or pct == 0:
            negative_factors.append(f"{m_id} has no weight (missing, rejected by QC, or excluded); the others were re-normalised.")
        elif pct >= 25:
            positive_factors.append(f"{m_id}: {pct}% weight; historical MAE {mae if mae is not None else 'n/a'} from {ev}.")
        else:
            negative_factors.append(f"{m_id}: only {pct}% weight; historical MAE {mae if mae is not None else 'n/a'} from {ev}.")

    if disagreement_info["disagreement_level"] == "HIGH":
        negative_factors.append(f"High multi-model divergence (spread: {disagreement_info['std_dev']} { 'mm' if variable=='rainfall' else ''}) reduces consensus confidence to {uncertainty_info['confidence']}.")
    else:
        positive_factors.append(f"Model convergence is {disagreement_info['disagreement_level']}, yielding consistent solution consensus.")

    # Synthesize plain, technically rigorous explanation using LLM provider (Grok / Deterministic template fallback)
    computed_facts = {
        "region_id": context.get("region_id"),
        "variable": variable,
        "lead_hours": lead_hours,
        "weather_regime": regime,
        "fused_value": fused_value,
        "dominant_model": dominant_id,
        "dominant_weight_pct": dominant_pct,
        "dominant_evidence": {
            "DATABASE_VERIFIED_HISTORY": "verified error history for this region",
            "SEEDED_PRIOR": "a seeded prior that is not yet verified here",
            "BOOTSTRAP_PRIOR": "a bootstrap prior (no verified history yet)",
            "SCENARIO_PRIOR": "the synthetic scenario's prior skill",
        }.get(evidence.get(dominant_id), "its prior skill estimate"),
        "probability": uncertainty_info["probability"],
        "confidence": uncertainty_info["confidence"],
        "disagreement_level": disagreement_info["disagreement_level"],
        "positive_factors": positive_factors,
        "negative_factors": negative_factors
    }
    summary_text = llm_service.generate_briefing(computed_facts)

    return {
        "fusion_result_id": "",
        "explanation_type": "WHY_THIS_FORECAST",
        "factors": {
            "positive_factors": positive_factors,
            "negative_factors": negative_factors,
            "dominant_model": dominant_id,
            "disagreement_level": disagreement_info["disagreement_level"],
            "confidence_rationale": uncertainty_info.get("rationale", ""),
            "weights_summary": {w["model_id"]: round(w["weight"], 3) for w in weights}
        },
        "text": summary_text,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


def compute_what_changed(
    current_fusion: Dict[str, Any],
    previous_fusion: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compares the current forecast cycle against the previous cycle to provide
    transparent operational delta diagnostics.
    """
    prev_val = previous_fusion.get("fused_value", 45.0)
    curr_val = current_fusion.get("fused_value", 70.0)
    val_diff = round(curr_val - prev_val, 1)

    prev_prob = previous_fusion.get("probability", 35.0)
    curr_prob = current_fusion.get("probability", 72.0)
    prob_diff = round(curr_prob - prev_prob, 1)

    prev_disagree = previous_fusion.get("disagreement", "LOW")
    curr_disagree = current_fusion.get("disagreement", "HIGH")

    # Shift drivers
    drivers = []
    if abs(val_diff) >= 15.0:
        drivers.append(f"Significant intensity {'escalation' if val_diff > 0 else 'reduction'} of {val_diff:+.1f} versus the previous cycle.")
    elif abs(val_diff) >= 1.0:
        drivers.append(f"Fused value revised by {val_diff:+.1f} versus the previous cycle.")
    if abs(prob_diff) > 10.0:
        drivers.append(f"Threshold-exceedance indicator moved {prob_diff:+.1f} percentage points across the forecast cycle.")
    if prev_disagree != curr_disagree:
        drivers.append(f"Model spread shifted from {prev_disagree} to {curr_disagree}.")

    primary_driver = " | ".join(drivers) if drivers else "Nominal cycle update with minor synoptic refinement."

    return {
        "previous_value": prev_val,
        "current_value": curr_val,
        "value_change": val_diff,
        "previous_probability": prev_prob,
        "current_probability": curr_prob,
        "probability_change_pct_points": prob_diff,
        "disagreement_shift": f"{prev_disagree} -> {curr_disagree}",
        "confidence_shift": f"{previous_fusion.get('confidence', 'HIGH')} -> {current_fusion.get('confidence', 'MEDIUM')}",
        "primary_driver": primary_driver,
        "model_shifts": {
            m: round((current_fusion.get("model_forecasts", {}).get(m) or 0.0) - (previous_fusion.get("model_forecasts", {}).get(m) or 0.0), 1)
            for m in current_fusion.get("model_forecasts", {})
        }
    }
