from typing import Dict, Any, Optional

class FailureMemoryEngine:
    """
    Tracks conditional model failure patterns across regimes and lead times,
    and maintains simulated failure injection states for stress testing.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FailureMemoryEngine, cls).__new__(cls)
            cls._instance._injected_bias = {}  # {model_id: bias_value}
            cls._instance._disabled_models = set()  # {model_id}
            cls._instance._forced_disagreement = False
        return cls._instance

    def inject_model_bias(self, model_id: str, bias_magnitude: float = 25.0):
        self._injected_bias[model_id] = bias_magnitude

    def disable_model(self, model_id: str):
        self._disabled_models.add(model_id)

    def force_disagreement(self, enable: bool = True):
        self._forced_disagreement = enable

    def reset(self):
        self._injected_bias.clear()
        self._disabled_models.clear()
        self._forced_disagreement = False

    def get_injected_bias(self, model_id: str) -> float:
        return self._injected_bias.get(model_id, 0.0)

    def is_model_disabled(self, model_id: str) -> bool:
        return model_id in self._disabled_models

    def is_forced_disagreement(self) -> bool:
        return self._forced_disagreement

    def evaluate_historical_vulnerability(
        self,
        model_id: str,
        weather_regime: str,
        lead_hours: int,
        season: str = "SW_MONSOON"
    ) -> Dict[str, Any]:
        """
        Retrieves known physical model vulnerability profiles based on
        documented Indian NWP and AI model characteristics:
        - NCUM: Excellent synoptic monsoon dynamics, but slight overestimation at 72h during convective transitions.
        - WRF: High-resolution mesoscale strength at 24h/48h; higher boundary condition dispersion at 72h.
        - GFS: Global coverage strength, but known wet-bias tendency in Indian peninsula during heavy monsoon regimes.
        - AI_WEATHER: Strong global pattern consistency, but occasionally under-predicts localized convective peak intensities.
        """
        vulnerability_score = 1.0  # 1.0 = normal reliability, < 1.0 = penalized
        reasons = []

        if model_id == "WRF" and lead_hours >= 72:
            vulnerability_score *= 0.78
            reasons.append("Higher mesoscale boundary dispersion at 72h lead time")
            
        if model_id == "GFS" and weather_regime == "HEAVY_RAINFALL":
            vulnerability_score *= 0.82
            reasons.append("Historical tendency for spatial precipitation spread and wet bias in peninsular monsoon")
            
        if model_id == "AI_WEATHER" and weather_regime == "CONVECTIVE":
            vulnerability_score *= 0.80
            reasons.append("AI grid resolution smooths extreme convective peak rainfall spikes")
            
        if model_id == "NCUM" and weather_regime == "HEAVY_RAINFALL":
            vulnerability_score *= 1.15  # Advantage under active monsoon
            reasons.append("NCUM has optimized 4D-Var data assimilation for Indian monsoon trough dynamics")

        # Injected bias penalty
        if model_id in self._injected_bias:
            bias_val = self._injected_bias[model_id]
            vulnerability_score *= max(0.2, 1.0 - (abs(bias_val) / 35.0))
            reasons.append(f"Recent operational bias drift detected ({bias_val:+.1f} mm)")

        return {
            "model_id": model_id,
            "vulnerability_multiplier": round(vulnerability_score, 3),
            "reasons": reasons
        }

failure_memory = FailureMemoryEngine()
