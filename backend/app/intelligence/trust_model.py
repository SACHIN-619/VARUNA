"""
VARUNA Adaptive Trust Architecture (Level 1: Adaptive Reliability Baseline).
SIH 2026 Problem Statement: SIH26081

Computes dynamic trust weights w_i based on historical skill, causal recent error,
synoptic weather regime, and forecast lead time.

Guarantees:
1. Simplex invariant: w_i >= 0.0, sum(w_i) == 1.0 (for active models)
2. Graceful degradation: missing or failed models are rebalanced without crash
3. Single remaining model returns status 'DEGRADED_SINGLE_SOURCE'
4. Zero valid models returns status 'FAILED_NO_SOURCES'
"""

from typing import Dict, List, Any, Optional
import numpy as np
from app.intelligence.reliability import compute_model_reliability
from app.intelligence.failure_memory import failure_memory


def compute_adaptive_weights(
    model_forecasts: Dict[str, Optional[float]],
    historical_skills: Dict[str, Dict[str, float]],
    recent_errors: Dict[str, float],
    context: Dict[str, Any],
    disagreement_info: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Computes dynamic, adaptive trust weights across all forecast sources.
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

    weights_list = []

    # Case 1: Zero active models -> Failure state
    if not active_models:
        for model_id in model_forecasts.keys():
            weights_list.append({
                "model_id": model_id,
                "weight": 0.0,
                "raw_forecast": model_forecasts.get(model_id),
                "historical_mae": historical_skills.get(model_id, {}).get("MAE", 14.0),
                "recent_bias": failure_memory.get_injected_bias(model_id),
                "confidence_contribution": 0.0,
                "status": "FAILED_NO_SOURCES",
                "notes": ["All forecast sources are unavailable or deactivated. No fusion possible."]
            })
        return weights_list

    # Case 2: Exactly 1 active model -> Degraded single source
    if len(active_models) == 1:
        single_id = active_models[0]
        for model_id in model_forecasts.keys():
            is_active = (model_id == single_id)
            weights_list.append({
                "model_id": model_id,
                "weight": 1.0 if is_active else 0.0,
                "raw_forecast": model_forecasts.get(model_id),
                "historical_mae": historical_skills.get(model_id, {}).get("MAE", 14.0),
                "recent_bias": failure_memory.get_injected_bias(model_id),
                "confidence_contribution": 0.25 if is_active else 0.0,
                "status": "DEGRADED_SINGLE_SOURCE" if is_active else "EXCLUDED",
                "notes": [
                    "Single remaining model feed active; ensemble consensus and multi-model blend unavailable."
                ] if is_active else ["Model feed unavailable."]
            })
        return weights_list

    # Case 3: Multiple active models -> Optimal adaptive simplex
    total_score = sum(raw_scores[m] for m in active_models)

    for model_id in model_forecasts.keys():
        if model_id in active_models:
            w = raw_scores[model_id] / total_score
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

    # Exact normalization enforcement: sum(w) == 1.0
    active_items = [item for item in weights_list if item["status"] == "ACTIVE"]
    if active_items:
        current_sum = sum(item["weight"] for item in active_items)
        for item in active_items:
            item["weight"] = round(item["weight"] / current_sum, 4)
        diff = 1.0 - sum(item["weight"] for item in active_items)
        if abs(diff) > 1e-6:
            max_item = max(active_items, key=lambda x: x["weight"])
            max_item["weight"] = round(max_item["weight"] + diff, 4)

    return weights_list
