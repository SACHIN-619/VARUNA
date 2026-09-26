from typing import Dict, List, Any
import numpy as np

STATIC_WEIGHTS_DEFAULT = {
    "NCUM": 0.40,
    "WRF": 0.30,
    "GFS": 0.20,
    "AI_WEATHER": 0.10
}

def perform_forecast_fusion(
    model_forecasts: Dict[str, float],
    weights: List[Dict[str, Any]],
    variable: str = "rainfall"
) -> Dict[str, Any]:
    """
    Combines heterogeneous model forecasts into an adaptive fused estimate,
    alongside baseline simple average and static blend estimates.
    """
    fused_val = 0.0
    active_forecasts = []
    
    # 1. Adaptive blend
    for item in weights:
        m_id = item["model_id"]
        w = item["weight"]
        f_val = model_forecasts.get(m_id)
        if f_val is not None and item.get("status") == "ACTIVE":
            fused_val += w * f_val
            active_forecasts.append(f_val)
            
    # 2. Baseline: Simple average
    simple_avg = float(np.mean(active_forecasts)) if active_forecasts else 0.0
    
    # 3. Baseline: Static blend (fixed operational heuristic)
    static_sum_w = 0.0
    static_val = 0.0
    for m_id, f_val in model_forecasts.items():
        if f_val is not None and m_id in STATIC_WEIGHTS_DEFAULT:
            static_val += STATIC_WEIGHTS_DEFAULT[m_id] * f_val
            static_sum_w += STATIC_WEIGHTS_DEFAULT[m_id]
    if static_sum_w > 0:
        static_val /= static_sum_w
    else:
        static_val = simple_avg

    # Precision formatting
    decimals = 1 if variable in ["rainfall", "temperature", "wind_speed"] else 2

    return {
        "fused_value": round(float(fused_val), decimals),
        "simple_average_value": round(float(simple_avg), decimals),
        "static_blend_value": round(float(static_val), decimals),
        "active_models_count": len(active_forecasts)
    }
