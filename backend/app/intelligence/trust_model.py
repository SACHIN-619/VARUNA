from typing import Dict, List, Any
import numpy as np
from app.intelligence.reliability import compute_model_reliability
from app.intelligence.failure_memory import failure_memory

def compute_adaptive_weights(
    model_forecasts: Dict[str, float],
    historical_skills: Dict[str, Dict[str, float]],
    recent_errors: Dict[str, float],
    context: Dict[str, Any],
    disagreement_info: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Computes dynamic, adaptive trust weights across all forecast sources.
    Guarantees:
      1. All weights w_i >= 0.0
      2. sum(w_i) == 1.0 (simplex constraint)
      3. Missing or disabled models are gracefully excluded and weights re-normalized
      4. Models with high recent error or historical regime weakness are penalized
    """
    raw_scores = {}
    reliability_metadata = {}
    active_models = []

    for model_id, raw_val in model_forecasts.items():
        # Check if model is missing or disabled in failure memory
        if raw_val is None or failure_memory.is_model_disabled(model_id):
            raw_scores[model_id] = 0.0
            reliability_metadata[model_id] = {
                "status": "DISABLED_OR_UNAVAILABLE",
                "notes": ["Model feed unavailable or deactivated in runtime controls."]
            }
            continue

        active_models.append(model_id)
        skill = historical_skills.get(model_id, {"MAE": 14.0, "BIAS": 0.0})
        hist_mae = skill.get("MAE", 14.0)
        rec_err = recent_errors.get(model_id, 0.0) + abs(failure_memory.get_injected_bias(model_id))

        rel = compute_model_reliability(
            model_id=model_id,
            historical_mae=hist_mae,
            recent_error=rec_err,
            context=context
        )
        reliability_metadata[model_id] = rel
        raw_scores[model_id] = max(1e-4, rel["composite_reliability"])

    # Simplex normalization
    total_score = sum(raw_scores[m] for m in active_models)

    weights_list = []
    if total_score > 0 and active_models:
        for model_id in model_forecasts.keys():
            if model_id in active_models:
                w = raw_scores[model_id] / total_score
                # Rounding with sum-preservation
                status = "ACTIVE"
            else:
                w = 0.0
                status = "EXCLUDED"

            rel = reliability_metadata.get(model_id, {})
            weights_list.append({
                "model_id": model_id,
                "weight": float(w),
                "raw_forecast": model_forecasts.get(model_id),
                "historical_mae": historical_skills.get(model_id, {}).get("MAE", 14.0),
                "recent_bias": failure_memory.get_injected_bias(model_id),
                "confidence_contribution": round(float(w * (1.0 - disagreement_info.get("disagreement_score", 0.0))), 3),
                "status": status,
                "notes": rel.get("notes", [])
            })
    else:
        # Fallback if no models are active
        n = len(model_forecasts)
        for model_id in model_forecasts.keys():
            weights_list.append({
                "model_id": model_id,
                "weight": 1.0 / n if n > 0 else 0.0,
                "raw_forecast": model_forecasts.get(model_id),
                "status": "FALLBACK_UNIFORM",
                "notes": ["All models deactivated; uniform emergency fallback applied."]
            })

    # Exact normalization enforcement: sum(w) == 1.0
    active_items = [item for item in weights_list if item["status"] == "ACTIVE"]
    if active_items:
        current_sum = sum(item["weight"] for item in active_items)
        for item in active_items:
            item["weight"] = round(item["weight"] / current_sum, 4)
        # Fix minor rounding delta on largest weight
        diff = 1.0 - sum(item["weight"] for item in active_items)
        if abs(diff) > 1e-6:
            max_item = max(active_items, key=lambda x: x["weight"])
            max_item["weight"] = round(max_item["weight"] + diff, 4)

    return weights_list
