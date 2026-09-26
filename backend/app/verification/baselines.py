from typing import List, Dict, Any
from app.verification.metrics import calculate_continuous_metrics, calculate_categorical_metrics, calculate_brier_score

def compare_fusion_baselines(
    dataset: List[Dict[str, Any]],
    variable: str = "rainfall",
    threshold: float = 64.5
) -> Dict[str, Any]:
    """
    Evaluates and compares the four standard baseline paradigms:
      1. Individual NWP/AI Models (NCUM, GFS, WRF, AI_WEATHER)
      2. Simple Multi-Model Average
      3. Static Operational Blend
      4. Adaptive AI Forecast Intelligence Blend (Varuna)
    """
    observations = [row["observation"] for row in dataset]
    
    models = ["NCUM", "GFS", "WRF", "AI_WEATHER"]
    methods_summary = []
    
    # 1. Individual models
    for m in models:
        f_vals = [row["forecasts"].get(m, 0.0) for row in dataset]
        c_metrics = calculate_continuous_metrics(f_vals, observations)
        cat_metrics = calculate_categorical_metrics(f_vals, observations, threshold=threshold)
        
        methods_summary.append({
            "method": "INDIVIDUAL_MODEL",
            "model_id": m,
            "mae": c_metrics["mae"],
            "rmse": c_metrics["rmse"],
            "bias": c_metrics["bias"],
            "correlation": c_metrics["correlation"],
            "pod": cat_metrics["pod"],
            "far": cat_metrics["far"],
            "csi": cat_metrics["csi"],
            "brier": None
        })
        
    # 2. Simple Average
    f_avg = [row["simple_average"] for row in dataset]
    c_avg = calculate_continuous_metrics(f_avg, observations)
    cat_avg = calculate_categorical_metrics(f_avg, observations, threshold=threshold)
    methods_summary.append({
        "method": "SIMPLE_AVERAGE",
        "model_id": None,
        "mae": c_avg["mae"],
        "rmse": c_avg["rmse"],
        "bias": c_avg["bias"],
        "correlation": c_avg["correlation"],
        "pod": cat_avg["pod"],
        "far": cat_avg["far"],
        "csi": cat_avg["csi"],
        "brier": None
    })
    
    # 3. Static Blend
    f_static = [row["static_blend"] for row in dataset]
    c_static = calculate_continuous_metrics(f_static, observations)
    cat_static = calculate_categorical_metrics(f_static, observations, threshold=threshold)
    methods_summary.append({
        "method": "STATIC_BLEND",
        "model_id": None,
        "mae": c_static["mae"],
        "rmse": c_static["rmse"],
        "bias": c_static["bias"],
        "correlation": c_static["correlation"],
        "pod": cat_static["pod"],
        "far": cat_static["far"],
        "csi": cat_static["csi"],
        "brier": None
    })
    
    # 4. Adaptive AI Blend
    f_adaptive = [row["adaptive_blend"] for row in dataset]
    c_adaptive = calculate_continuous_metrics(f_adaptive, observations)
    cat_adaptive = calculate_categorical_metrics(f_adaptive, observations, threshold=threshold)
    probs_adaptive = [row.get("probability", 50.0) for row in dataset]
    brier_adaptive = calculate_brier_score(probs_adaptive, observations, threshold=threshold)
    
    methods_summary.append({
        "method": "ADAPTIVE_BLEND",
        "model_id": None,
        "mae": c_adaptive["mae"],
        "rmse": c_adaptive["rmse"],
        "bias": c_adaptive["bias"],
        "correlation": c_adaptive["correlation"],
        "pod": cat_adaptive["pod"],
        "far": cat_adaptive["far"],
        "csi": cat_adaptive["csi"],
        "brier": brier_adaptive
    })
    
    # Calculate percentage reduction in MAE compared to simple average
    simple_mae = c_avg["mae"]
    adaptive_mae = c_adaptive["mae"]
    reduction_pct = round(((simple_mae - adaptive_mae) / simple_mae) * 100.0, 1) if simple_mae > 0 else 0.0

    return {
        "variable": variable,
        "sample_size": len(dataset),
        "methods": methods_summary,
        "adaptive_advantage_mae_reduction_pct": reduction_pct,
        "observation_provenance": "historical_evaluation_split"
    }
