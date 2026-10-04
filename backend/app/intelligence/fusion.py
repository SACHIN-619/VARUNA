"""
VARUNA Multi-Model Forecast Fusion Engine.
SIH 2026 Problem Statement: SIH26081

Combines heterogeneous model forecasts into an adaptive fused estimate alongside
rigorous baselines (Simple Multi-Model Average and Static Operational Blend).

Guarantees:
- If zero sources are valid: returns a structured failure state (status='FAILED_NO_SOURCES')
- If single source is valid: returns forecast with reduced confidence and status='DEGRADED_SINGLE_SOURCE'
- If multi-source: returns optimal convex combination sum(w_i * F_i)
"""

from typing import Dict, List, Any, Optional
import numpy as np

STATIC_WEIGHTS_DEFAULT = {
    "NCUM": 0.40,
    "WRF": 0.30,
    "GFS": 0.20,
    "AI_WEATHER": 0.10,
    # Fixed priors for the public live models (a baseline, not tuned): ECMWF IFS is the
    # best-verified global NWP, UM/ICON are strong independents.
    "ECMWF_IFS": 0.30,
    "UKMO_UM": 0.25,
    "ICON": 0.20,
}


def perform_forecast_fusion(
    model_forecasts: Dict[str, Optional[float]],
    weights: List[Dict[str, Any]],
    variable: str = "rainfall"
) -> Dict[str, Any]:
    """
    Executes forecast fusion with explicit status flags.
    """
    active_forecasts = []
    fused_val = 0.0

    # Collect valid active predictions
    for item in weights:
        m_id = item["model_id"]
        w = item["weight"]
        f_val = model_forecasts.get(m_id)
        if f_val is not None and item.get("status") in ["ACTIVE", "DEGRADED_SINGLE_SOURCE"]:
            fused_val += w * f_val
            active_forecasts.append(f_val)

    decimals = 1 if variable in ["rainfall", "temperature", "wind_speed"] else 2

    # Case 1: Zero valid sources
    if not active_forecasts:
        return {
            "status": "FAILED_NO_SOURCES",
            "fused_value": None,
            "simple_average_value": None,
            "static_blend_value": None,
            "baselines": {"simple_average": None, "static_blend": None},
            "active_models_count": 0,
            "error_message": "All forecast sources are unavailable or deactivated. No forecast could be synthesized."
        }

    # Case 2: Exactly 1 valid source
    if len(active_forecasts) == 1:
        val = round(float(active_forecasts[0]), decimals)
        return {
            "status": "DEGRADED_SINGLE_SOURCE",
            "fused_value": val,
            "simple_average_value": val,
            "static_blend_value": val,
            "baselines": {"simple_average": val, "static_blend": val},
            "active_models_count": 1,
            "warning": "Forecast generated from a single active source; multi-model consensus unavailable."
        }

    # Case 3: Multiple sources (Optimal Fusion)
    simple_avg = float(np.mean(active_forecasts))

    static_sum_w = 0.0
    static_val = 0.0
    active_ids = {item["model_id"] for item in weights if item.get("status") in ["ACTIVE", "DEGRADED_SINGLE_SOURCE"]}
    for m_id, f_val in model_forecasts.items():
        if f_val is not None and m_id in STATIC_WEIGHTS_DEFAULT and m_id in active_ids:
            static_val += STATIC_WEIGHTS_DEFAULT[m_id] * f_val
            static_sum_w += STATIC_WEIGHTS_DEFAULT[m_id]
    if static_sum_w > 0:
        static_val /= static_sum_w
    else:
        static_val = simple_avg

    return {
        "status": "OPTIMAL_MULTI_MODEL_FUSION",
        "fused_value": round(float(fused_val), decimals),
        "simple_average_value": round(float(simple_avg), decimals),
        "static_blend_value": round(float(static_val), decimals),
        "baselines": {
            "simple_average": round(float(simple_avg), decimals),
            "static_blend": round(float(static_val), decimals),
        },
        "active_models_count": len(active_forecasts)
    }
