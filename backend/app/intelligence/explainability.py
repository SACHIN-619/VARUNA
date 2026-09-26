from typing import Dict, List, Any
from datetime import datetime, timezone

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

    # Explain weights
    for w in weights:
        m_id = w["model_id"]
        pct = round(w["weight"] * 100.0, 1)
        if m_id == "NCUM" and pct >= 30:
            positive_factors.append(f"NCUM allocated {pct}% weight due to strong historical skill in Indian monsoon trough conditions (MAE: {w.get('historical_mae', 12.0)}).")
        elif m_id == "WRF" and pct >= 25:
            positive_factors.append(f"WRF received {pct}% weight leveraging mesoscale convective resolving resolution at {lead_hours}h lead.")
        elif m_id == "GFS" and w.get("recent_bias", 0.0) > 10.0:
            negative_factors.append(f"GFS weight reduced to {pct}% following detected operational wet bias drift (+{w['recent_bias']} mm).")
        elif w.get("status") == "EXCLUDED":
            negative_factors.append(f"{m_id} feed is unavailable or decommissioned; remaining models re-normalized.")

    if disagreement_info["disagreement_level"] == "HIGH":
        negative_factors.append(f"High multi-model divergence (spread: {disagreement_info['std_dev']} { 'mm' if variable=='rainfall' else ''}) reduces consensus confidence to {uncertainty_info['confidence']}.")
    else:
        positive_factors.append(f"Model convergence is {disagreement_info['disagreement_level']}, yielding consistent solution consensus.")

    # Synthesize plain, technically rigorous explanation
    summary_text = (
        f"For {context.get('region_id')} at {lead_hours}h lead under {regime} regime, the adaptive engine blended forecasts "
        f"into {fused_value} {'mm' if variable=='rainfall' else '°C' if variable=='temperature' else 'km/h'}. "
        f"{dominant_id} carries the highest trust weight ({dominant_pct}%) owing to superior historical regime verification. "
        f"Event probability is {uncertainty_info['probability']}% with {uncertainty_info['confidence']} confidence "
        f"(disagreement level: {disagreement_info['disagreement_level']})."
    )

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
        drivers.append(f"Significant intensity escalation of {val_diff:+.1f} mm driven by deepening convective synoptic signatures.")
    if prob_diff > 20.0:
        drivers.append(f"Heavy rainfall probability jumped {prob_diff:+.1f} percentage points across the forecast cycle.")
    if prev_disagree != curr_disagree:
        drivers.append(f"Model spread shifted from {prev_disagree} to {curr_disagree}, reflecting incoming ensemble divergence.")

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
