"""
VARUNA Disagreement-Aware Uncertainty & Confidence Engine.
SIH 2026 Problem Statement: SIH26081

SCIENTIFIC INTEGRITY ENFORCEMENT (Phase 12):
Strictly distinguishes between:
1. Multi-Model Disagreement / Spread: Epistemic divergence across NWP and AI physics
2. Epistemic Confidence Rating: Operational confidence that model consensus is reliable
3. Hazard Exceedance Probability Indicator: Uncalibrated Gaussian surrogate metric
   (clearly marked is_calibrated_probability=False to avoid false claims of frequentist probability)
4. Predictive Uncertainty Interval: Quantified margin of error (+/- mm, °C, m/s)
"""

from typing import Dict, Any, List, Optional
import scipy.stats as stats
import numpy as np
from app.core.config import settings


def compute_uncertainty_and_confidence(
    fused_value: Optional[float],
    model_forecasts: Dict[str, Optional[float]],
    weights: List[Dict[str, Any]],
    disagreement_info: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes rigorous uncertainty metrics with complete separation of confidence and probability.
    """
    if fused_value is None:
        return {
            "probability": 0.0,
            "probability_indicator": 0.0,
            "is_calibrated_probability": False,
            "confidence": "NONE",
            "confidence_score": 0.0,
            "uncertainty_margin": 0.0,
            "threshold": 0.0,
            "spread_metrics": disagreement_info,
            "rationale": "No active forecast feeds available; uncertainty cannot be quantified."
        }

    variable = context.get("variable", "rainfall")
    lead_hours = context.get("lead_hours", 48)
    disagreement_score = disagreement_info.get("disagreement_score", 0.0)
    std_dev = disagreement_info.get("forecast_spread") or disagreement_info.get("std_dev", 5.0)

    # 1. Epistemic Confidence Calculation (1.0 = absolute consensus, 0.0 = total divergence)
    conf_base = 1.0 - (0.55 * disagreement_score)

    # Penalty for missing feeds
    active_count = sum(1 for w in weights if w.get("status") in ["ACTIVE", "DEGRADED_SINGLE_SOURCE"])
    total_expected = len(weights)
    missing_ratio = (total_expected - active_count) / max(1, total_expected)
    conf_base -= (0.25 * missing_ratio)

    # Penalty for single-source mode
    if active_count == 1:
        conf_base = min(conf_base, 0.35)

    # Lead-time decay penalty
    lead_decay = max(0.0, (lead_hours - 24) / 100.0)
    conf_base -= (0.20 * lead_decay)

    confidence_score = max(0.10, min(0.95, conf_base))

    if active_count == 1:
        confidence_level = "LOW"
    elif confidence_score >= 0.70:
        confidence_level = "HIGH"
    elif confidence_score >= 0.45:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

    # 2. Extreme Weather Threshold
    if variable == "rainfall":
        threshold = settings.HEAVY_RAINFALL_THRESHOLD_MM
    elif variable == "temperature":
        threshold = settings.HIGH_TEMP_THRESHOLD_C
    else:
        threshold = 14.0  # m/s gale threshold (~50 km/h)

    # Predictive standard deviation incorporating lead time and multi-model spread
    sigma = max(2.5, std_dev * (1.0 + lead_decay))

    # Probability indicator (Gaussian parametric surrogate)
    z = (threshold - fused_value) / sigma
    prob_exceed = float((1.0 - stats.norm.cdf(z)) * 100.0)
    prob_indicator = round(max(1.0, min(99.0, prob_exceed)), 1)

    # Quantitative uncertainty margin (~80% prediction interval)
    uncertainty_margin = round(float(1.28 * sigma), 1)

    rationale_parts = []
    if disagreement_info.get("disagreement_level") == "HIGH":
        rationale_parts.append("High multi-model spread indicates divergent synoptic evolution between physical and AI dynamics.")
    else:
        rationale_parts.append("Model consensus across physical NWP and AI outputs supports stable blending confidence.")

    if active_count == 1:
        rationale_parts.append("Reduced to single-model mode; multi-model consensus verification is unavailable.")
    elif active_count < total_expected:
        rationale_parts.append(f"{total_expected - active_count} forecast feed(s) unavailable; remaining feeds re-normalized.")

    if lead_hours >= 72:
        rationale_parts.append("72-hour lead time exhibits intrinsic atmospheric predictability limits.")

    components = {
        "disagreement_score": round(float(disagreement_score), 3),
        "missing_ratio": round(float(missing_ratio), 3),
        "lead_decay": round(float(lead_decay), 3),
        "active_count": active_count,
        "total_expected": total_expected,
        "confidence_formula": "C = clip(1 - 0.55*D - 0.25*missing - 0.20*leadDecay, 0.10, 0.95); single source caps C at 0.35",
        "sigma": round(float(sigma), 3),
        "sigma_formula": "sigma = max(2.5, spread * (1 + leadDecay)), leadDecay = max(0, (lead-24)/100)",
        "probability_formula": "P(X >= T) ~ 1 - Phi((T - F) / sigma)  [uncalibrated Gaussian indicator]",
        "z_score": round(float(z), 3),
        "margin_formula": "+/- 1.28*sigma (approx. 80% interval)",
    }

    return {
        "components": components,
        "probability": prob_indicator,
        "probability_indicator": prob_indicator,
        "is_calibrated_probability": False,
        "confidence": confidence_level,
        "confidence_score": round(confidence_score, 3),
        "uncertainty_margin": uncertainty_margin,
        "threshold": threshold,
        "spread_metrics": {
            "forecast_spread": disagreement_info.get("forecast_spread", std_dev),
            "weighted_spread": disagreement_info.get("weighted_spread", std_dev),
            "range": disagreement_info.get("range", 0.0),
            "variance": disagreement_info.get("variance", 0.0)
        },
        "rationale": " ".join(rationale_parts)
    }
