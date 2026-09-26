from typing import Dict, List, Any
import numpy as np

def extract_features(
    model_forecasts: Dict[str, float],
    historical_skills: Dict[str, Dict[str, float]],
    recent_errors: Dict[str, float],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extracts structured meteorological features for adaptive trust estimation.
    Includes forecast values, historical skill metrics (MAE, RMSE, Bias),
    recent cycle errors, lead time decay, and regime indicators.
    """
    features = {}
    active_models = [m for m, val in model_forecasts.items() if val is not None]
    
    # 1. Model forecast values
    features["raw_forecasts"] = {m: model_forecasts.get(m, 0.0) for m in active_models}
    
    # 2. Historical MAE / RMSE
    features["historical_mae"] = {}
    features["historical_bias"] = {}
    for m in active_models:
        skill = historical_skills.get(m, {})
        features["historical_mae"][m] = skill.get("MAE", 15.0)
        features["historical_bias"][m] = skill.get("BIAS", 0.0)
        
    # 3. Recent short-term errors (reflecting model drift or bias)
    features["recent_errors"] = {m: recent_errors.get(m, 0.0) for m in active_models}
    
    # 4. Contextual descriptors
    features["lead_hours"] = context.get("lead_hours", 48)
    features["weather_regime"] = context.get("weather_regime", "NORMAL")
    features["season"] = context.get("season", "SW_MONSOON")
    features["region_id"] = context.get("region_id", "IN_TELANGANA_HYDERABAD")
    
    return features
