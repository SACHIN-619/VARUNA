from typing import Dict, Any, List
import scipy.stats as stats
import numpy as np
from app.core.config import settings

def compute_uncertainty_and_confidence(
    fused_value: float,
    model_forecasts: Dict[str, float],
    weights: List[Dict[str, Any]],
    disagreement_info: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes rigorous uncertainty bounds, calibrated extreme-event probability,
    and an epistemic confidence rating that is strictly separated from event probability.
    """
    variable = context.get("variable", "rainfall")
    lead_hours = context.get("lead_hours", 48)
    disagreement_score = disagreement_info.get("disagreement_score", 0.0)
    std_dev = disagreement_info.get("std_dev", 5.0)

    # 1. Epistemic Confidence Calculation (1.0 = absolute consensus, 0.0 = total divergence)
    # Penalties:
    # a. Disagreement penalty
    conf_base = 1.0 - (0.55 * disagreement_score)

    # b. Missing model penalty
    active_count = sum(1 for w in weights if w.get("status") == "ACTIVE")
    total_expected = len(weights)
    missing_ratio = (total_expected - active_count) / max(1, total_expected)
    conf_base -= (0.25 * missing_ratio)

    # c. Lead-time decay penalty (72h has higher intrinsic forecast horizon uncertainty)
    lead_decay = (lead_hours - 24) / 100.0  # 0 for 24h, 0.24 for 48h, 0.48 for 72h
    conf_base -= (0.20 * lead_decay)

    confidence_score = max(0.15, min(0.95, conf_base))

    if confidence_score >= 0.70:
        confidence_level = "HIGH"
    elif confidence_score >= 0.45:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

    # 2. Probability of Extreme Event
    # Define thresholds
    if variable == "rainfall":
        threshold = settings.HEAVY_RAINFALL_THRESHOLD_MM
    elif variable == "temperature":
        threshold = settings.HIGH_TEMP_THRESHOLD_C
    else:
        threshold = settings.HIGH_WIND_THRESHOLD_KMH

    # Effective predictive standard deviation incorporating lead time and multi-model spread
    sigma = max(3.0, std_dev * (1.0 + lead_decay))

    # Probability of exceeding threshold: 1 - CDF(threshold)
    # Using Gaussian predictive density centered at fused_value with predictive sigma
    z = (threshold - fused_value) / sigma
    prob_exceed = float((1.0 - stats.norm.cdf(z)) * 100.0)
    prob_exceed = round(max(1.0, min(99.0, prob_exceed)), 1)

    # 3. Quantitative uncertainty margin (+/- mm, C, or km/h) representing ~80% prediction interval
    uncertainty_margin = round(float(1.28 * sigma), 1)

    # Detailed rationale for confidence
    rationale = []
    if disagreement_info.get("disagreement_level") == "HIGH":
        rationale.append("Significant divergence between physical NWP and AI model outputs reduces consensus reliability.")
    else:
        rationale.append("High model convergence across deterministic and regional solutions supports higher confidence.")

    if active_count < total_expected:
        rationale.append(f"{total_expected - active_count} forecast feed(s) unavailable, rebalancing dynamic weights.")

    if lead_hours == 72:
        rationale.append("72-hour forecast horizon introduces non-linear synoptic evolution uncertainty.")

    return {
        "probability": prob_exceed,
        "confidence": confidence_level,
        "confidence_score": round(confidence_score, 3),
        "uncertainty_margin": uncertainty_margin,
        "threshold": threshold,
        "rationale": " ".join(rationale)
    }
