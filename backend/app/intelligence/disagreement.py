"""
VARUNA Multi-Model Disagreement Engine.
SIH 2026 Problem Statement: SIH26081

Computes rigorous multi-model disagreement metrics:
- Standard deviation (ensemble spread)
- Weighted ensemble spread
- Inter-model range (max - min)
- Multi-model variance
- Normalized spread score
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np


def calculate_disagreement(
    forecasts: Dict[str, Optional[float]],
    variable: str = "rainfall",
    weights: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Computes rigorous multi-model disagreement metrics.
    Treats forecast divergence as an epistemic uncertainty indicator.
    """
    active_pairs = [(m, float(v)) for m, v in forecasts.items() if v is not None]
    
    if len(active_pairs) < 2:
        val = active_pairs[0][1] if active_pairs else 0.0
        return {
            "disagreement_level": "LOW",
            "disagreement_score": 0.0,
            "std_dev": 0.0,
            "forecast_spread": 0.0,
            "weighted_spread": 0.0,
            "range": 0.0,
            "variance": 0.0,
            "normalized_spread": 0.0,
            "min_forecast": val,
            "max_forecast": val,
            "contributing_models": [p[0] for p in active_pairs],
            "active_count": len(active_pairs),
            "interpretation": "Single model available or unanimous consensus." if active_pairs else "Zero active forecast sources."
        }
        
    vals = [p[1] for p in active_pairs]
    arr = np.array(vals)
    mean_val = float(np.mean(arr))
    variance_val = float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0
    std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    val_range = float(np.max(arr) - np.min(arr))
    
    # Weighted spread if weights provided
    weighted_spread = std_val
    if weights:
        w_map = {item["model_id"]: item.get("weight", 0.0) for item in weights if item.get("status") == "ACTIVE"}
        w_vals = [w_map.get(p[0], 1.0 / len(active_pairs)) for p in active_pairs]
        sum_w = sum(w_vals)
        if sum_w > 0:
            norm_w = np.array(w_vals) / sum_w
            w_mean = np.sum(norm_w * arr)
            weighted_var = np.sum(norm_w * (arr - w_mean) ** 2)
            weighted_spread = float(np.sqrt(weighted_var))

    # Normalized spread calculation with epsilon to avoid division by zero
    epsilon = 5.0 if variable == "rainfall" else 2.0
    norm_spread = float(std_val / (abs(mean_val) + epsilon))
    
    # Variable-specific thresholds: (low_std, high_std, low_range, high_range).
    # Score is a continuous, monotone function of spread (the previous piecewise
    # version was discontinuous: e.g. std=3 mm with range=25 mm scored 0.36 as
    # "MODERATE", lower than a "LOW" case).
    thresholds = {
        "rainfall": (10.0, 25.0, 20.0, 55.0),
        "temperature": (1.5, 3.5, 3.0, 8.0),
    }.get(variable, (2.0, 5.0, 4.0, 12.0))
    lo_s, hi_s, lo_r, hi_r = thresholds
    if std_val < lo_s:
        score = 0.5 * std_val / lo_s
    elif std_val < hi_s:
        score = 0.5 + 0.3 * (std_val - lo_s) / (hi_s - lo_s)
    else:
        score = 0.8 + 0.2 * min(1.0, (std_val - hi_s) / hi_s)
    rank_std = 0 if std_val < lo_s else (1 if std_val < hi_s else 2)
    rank_rng = 0 if val_range < lo_r else (1 if val_range < hi_r else 2)
    rank = max(rank_std, rank_rng)
    level = ["LOW", "MODERATE", "HIGH"][rank]
    score = max(score, [0.0, 0.5, 0.8][rank])
    score = min(1.0, score)

    interpretation = (
        f"Multi-model spread is {level} (std: {std_val:.1f}, range: {val_range:.1f}, variance: {variance_val:.1f}). "
        f"{'High model divergence indicates significant synoptic uncertainty.' if level == 'HIGH' else 'High agreement enhances forecast consensus confidence.'}"
    )

    return {
        "disagreement_level": level,
        "disagreement_score": round(score, 3),
        "std_dev": round(std_val, 2),
        "forecast_spread": round(std_val, 2),
        "weighted_spread": round(weighted_spread, 2),
        "range": round(val_range, 2),
        "variance": round(variance_val, 2),
        "normalized_spread": round(norm_spread, 3),
        "min_forecast": round(float(np.min(arr)), 1),
        "max_forecast": round(float(np.max(arr)), 1),
        "contributing_models": [p[0] for p in active_pairs],
        "active_count": len(active_pairs),
        "interpretation": interpretation
    }
