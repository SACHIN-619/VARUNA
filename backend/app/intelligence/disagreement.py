from typing import Dict, List, Tuple, Any
import numpy as np

def calculate_disagreement(
    forecasts: Dict[str, float],
    variable: str = "rainfall"
) -> Dict[str, Any]:
    """
    Computes rigorous multi-model disagreement metrics.
    Treats forecast divergence as a direct epistemic uncertainty indicator.
    """
    active_values = [float(v) for v in forecasts.values() if v is not None]
    
    if len(active_values) < 2:
        return {
            "disagreement_level": "LOW",
            "disagreement_score": 0.0,
            "std_dev": 0.0,
            "range": 0.0,
            "normalized_spread": 0.0,
            "min_forecast": active_values[0] if active_values else 0.0,
            "max_forecast": active_values[0] if active_values else 0.0,
            "contributing_models": list(forecasts.keys()),
            "interpretation": "Single model available or unanimous consensus."
        }
        
    arr = np.array(active_values)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    val_range = float(np.max(arr) - np.min(arr))
    
    # Normalized spread calculation with epsilon to avoid division by zero
    epsilon = 5.0 if variable == "rainfall" else 2.0
    norm_spread = float(std_val / (abs(mean_val) + epsilon))
    
    # Thresholds tailored to variable scale
    if variable == "rainfall":
        # Disagreement based on absolute spread (std dev in mm) and relative spread
        if std_val < 10.0 and val_range < 20.0:
            level = "LOW"
            score = min(1.0, std_val / 20.0)
        elif std_val < 25.0 and val_range < 55.0:
            level = "MODERATE"
            score = 0.5 + min(0.3, (std_val - 10.0) / 50.0)
        else:
            level = "HIGH"
            score = min(1.0, 0.8 + (std_val - 25.0) / 100.0)
    elif variable == "temperature":
        if std_val < 1.5:
            level = "LOW"
            score = std_val / 3.0
        elif std_val < 3.5:
            level = "MODERATE"
            score = 0.5 + (std_val - 1.5) / 4.0
        else:
            level = "HIGH"
            score = min(1.0, 0.85 + (std_val - 3.5) / 5.0)
    else: # wind_speed
        if std_val < 6.0:
            level = "LOW"
            score = std_val / 12.0
        elif std_val < 15.0:
            level = "MODERATE"
            score = 0.5 + (std_val - 6.0) / 18.0
        else:
            level = "HIGH"
            score = min(1.0, 0.85 + (std_val - 15.0) / 20.0)

    interpretation = (
        f"Multi-model spread is {level} (std: {std_val:.1f}, range: {val_range:.1f}). "
        f"{'High model divergence indicates significant synoptic uncertainty.' if level == 'HIGH' else 'High agreement enhances forecast consensus confidence.'}"
    )

    return {
        "disagreement_level": level,
        "disagreement_score": round(score, 3),
        "std_dev": round(std_val, 2),
        "range": round(val_range, 2),
        "normalized_spread": round(norm_spread, 3),
        "min_forecast": round(float(np.min(arr)), 1),
        "max_forecast": round(float(np.max(arr)), 1),
        "contributing_models": [m for m, v in forecasts.items() if v is not None],
        "interpretation": interpretation
    }
