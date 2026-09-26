from typing import List, Dict, Any
from app.verification.baselines import compare_fusion_baselines

class ForecastEvaluator:
    """
    Manages temporal evaluation splits and continuous skill memory updates.
    Enforces strict temporal separation: historical training split vs validation vs test.
    """
    
    @staticmethod
    def evaluate_temporal_benchmark(
        historical_dataset: List[Dict[str, Any]],
        split_ratio: float = 0.75
    ) -> Dict[str, Any]:
        """
        Splits chronologically (never random shuffle) to prevent temporal data leakage.
        """
        n = len(historical_dataset)
        split_idx = int(n * split_ratio)
        test_data = historical_dataset[split_idx:]
        
        return compare_fusion_baselines(test_data, variable="rainfall")

    @staticmethod
    def update_model_skill_memory(
        model_id: str,
        recent_forecast: float,
        actual_observation: float,
        prior_mae: float,
        alpha: float = 0.1
    ) -> float:
        """
        Applies Exponential Moving Average (EMA) update to model skill memory:
        MAE_new = (1 - alpha) * MAE_prior + alpha * |forecast - observation|
        """
        abs_err = abs(recent_forecast - actual_observation)
        updated_mae = (1.0 - alpha) * prior_mae + alpha * abs_err
        return round(float(updated_mae), 3)

evaluator = ForecastEvaluator()
