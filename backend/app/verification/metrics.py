import numpy as np
from typing import List, Dict, Any, Tuple

def calculate_continuous_metrics(forecasts: List[float], observations: List[float]) -> Dict[str, float]:
    """
    Computes standard continuous meteorological verification metrics:
    MAE, RMSE, Mean Bias Error (MBE), and Pearson Correlation.
    """
    f = np.array(forecasts, dtype=float)
    o = np.array(observations, dtype=float)
    
    if len(f) == 0 or len(o) == 0:
        return {"mae": 0.0, "rmse": 0.0, "bias": 0.0, "correlation": 0.0}
        
    errors = f - o
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    bias = float(np.mean(errors))
    
    # Pearson correlation
    if np.std(f) > 1e-6 and np.std(o) > 1e-6:
        corr = float(np.corrcoef(f, o)[0, 1])
    else:
        corr = 1.0 if np.allclose(f, o) else 0.0
        
    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "bias": round(bias, 2),
        "correlation": round(corr, 3)
    }

def calculate_categorical_metrics(
    forecasts: List[float], 
    observations: List[float], 
    threshold: float = 64.5
) -> Dict[str, float]:
    """
    Computes extreme-event contingency table verification metrics:
    - Probability of Detection (POD = Hits / (Hits + Misses))
    - False Alarm Ratio (FAR = False Alarms / (Hits + False Alarms))
    - Critical Success Index (CSI / Threat Score = Hits / (Hits + Misses + False Alarms))
    """
    f = np.array(forecasts, dtype=float)
    o = np.array(observations, dtype=float)
    
    f_event = (f >= threshold)
    o_event = (o >= threshold)
    
    hits = int(np.sum(f_event & o_event))
    misses = int(np.sum((~f_event) & o_event))
    false_alarms = int(np.sum(f_event & (~o_event)))
    correct_negatives = int(np.sum((~f_event) & (~o_event)))
    
    pod = hits / (hits + misses) if (hits + misses) > 0 else 1.0
    far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else 0.0
    csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) > 0 else 1.0
    
    return {
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "pod": round(float(pod), 3),
        "far": round(float(far), 3),
        "csi": round(float(csi), 3)
    }

def calculate_brier_score(probabilities: List[float], observations: List[float], threshold: float = 64.5) -> float:
    """
    Computes Brier Score for probabilistic extreme-weather guidance:
    BS = (1/N) * sum((prob - actual_binary)^2)
    where actual_binary is 1 if observation >= threshold, else 0.
    """
    probs = np.array(probabilities, dtype=float) / 100.0  # normalize 0-100% to 0-1
    actual = (np.array(observations, dtype=float) >= threshold).astype(float)
    return round(float(np.mean((probs - actual) ** 2)), 4)
