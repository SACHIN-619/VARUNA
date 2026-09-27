from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from app.demo.scenarios import SCENARIOS
from app.intelligence.context_engine import ContextEngine
from app.intelligence.disagreement import calculate_disagreement
from app.intelligence.failure_memory import failure_memory
from app.intelligence.trust_model import compute_adaptive_weights
from app.intelligence.fusion import perform_forecast_fusion
from app.intelligence.uncertainty import compute_uncertainty_and_confidence
from app.intelligence.explainability import generate_forecast_explanation, compute_what_changed
from app.intelligence.ml_trust_model import ml_trust_model

class ScenarioGenerator:
    def __init__(self):
        self.current_scenario_id = "SCENARIO_2_SIGNATURE_HEAVY_RAINFALL"

    def list_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "scenario_id": s["scenario_id"],
                "title": s["title"],
                "description": s["description"],
                "weather_regime": s["weather_regime"],
                "active_models": [m for m, v in s["forecasts"].items() if v is not None]
            }
            for s in SCENARIOS.values()
        ]

    def get_scenario(self, scenario_id: str) -> Dict[str, Any]:
        return SCENARIOS.get(scenario_id, SCENARIOS["SCENARIO_2_SIGNATURE_HEAVY_RAINFALL"])

    def set_active_scenario(self, scenario_id: str) -> bool:
        if scenario_id in SCENARIOS:
            self.current_scenario_id = scenario_id
            return True
        return False

    def execute_pipeline(
        self,
        scenario_id: Optional[str] = None,
        custom_forecasts: Optional[Dict[str, float]] = None,
        custom_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end scientific pipeline:
        Harmonization -> Context -> Disagreement -> Trust AI -> Fusion -> Uncertainty -> XAI
        """
        sc_id = scenario_id or self.current_scenario_id
        scenario = self.get_scenario(sc_id)

        # 1. Inputs & Harmonization
        forecasts = custom_forecasts or scenario["forecasts"].copy()
        
        # Apply failure memory modifications
        for m_id in list(forecasts.keys()):
            if failure_memory.is_model_disabled(m_id):
                forecasts[m_id] = None
            elif failure_memory.get_injected_bias(m_id) != 0.0 and forecasts[m_id] is not None:
                forecasts[m_id] = round(forecasts[m_id] + failure_memory.get_injected_bias(m_id), 1)

        # Forced disagreement injection if enabled
        if failure_memory.is_forced_disagreement():
            forecasts["GFS"] = round(forecasts.get("GFS", 70.0) + 45.0, 1)
            forecasts["WRF"] = round(max(2.0, forecasts.get("WRF", 50.0) - 35.0), 1)

        hist_skills = scenario.get("historical_skills", {})
        recent_errs = scenario.get("recent_errors", {})

        # 2. Context Engine
        ctx_in = dict(custom_context) if custom_context else {
            "region_id": scenario["region_id"],
            "season": scenario["season"],
            "lead_hours": scenario["lead_hours"],
            "variable": scenario["variable"],
            "weather_regime": scenario["weather_regime"]
        }
        selected_strategy = ctx_in.pop("strategy", "ADAPTIVE_ML")
        context = ContextEngine.build_context(**ctx_in)


        # 3. Disagreement Engine
        disagreement = calculate_disagreement(forecasts, variable=context["variable"])

        # 4. Adaptive Trust Engines (Both Heuristic Baseline & Supervised ML Meta-Model)
        heuristic_weights = compute_adaptive_weights(
            model_forecasts=forecasts,
            historical_skills=hist_skills,
            recent_errors=recent_errs,
            context=context,
            disagreement_info=disagreement
        )
        
        ml_weights = ml_trust_model.predict_weights(
            forecasts=forecasts,
            historical_skills=hist_skills,
            recent_errors=recent_errs,
            context=context
        )
        
        selected_strategy = custom_context.get("strategy", "ADAPTIVE_ML") if custom_context else "ADAPTIVE_ML"
        weights = ml_weights if selected_strategy == "ADAPTIVE_ML" else heuristic_weights

        # 5. Forecast Fusion
        fusion_out = perform_forecast_fusion(
            model_forecasts=forecasts,
            weights=weights,
            variable=context["variable"]
        )
        
        # Also compute heuristic baseline value
        heuristic_fusion = perform_forecast_fusion(
            model_forecasts=forecasts,
            weights=heuristic_weights,
            variable=context["variable"]
        )

        # 6. Uncertainty & Confidence Engine
        uncertainty = compute_uncertainty_and_confidence(
            fused_value=fusion_out["fused_value"],
            model_forecasts=forecasts,
            weights=weights,
            disagreement_info=disagreement,
            context=context
        )

        # 7. Explainability Engine (Why this forecast?)
        explanation = generate_forecast_explanation(
            fused_value=fusion_out["fused_value"],
            weights=weights,
            disagreement_info=disagreement,
            uncertainty_info=uncertainty,
            context=context
        )

        # 8. What Changed Diagnostics
        prev_cycle = scenario.get("previous_cycle", {
            "fused_value": round(fusion_out["fused_value"] * 0.75, 1),
            "probability": max(10.0, uncertainty["probability"] - 25.0),
            "confidence": "HIGH",
            "disagreement": "LOW",
            "model_forecasts": {m: round((v or 50.0) * 0.8, 1) for m, v in forecasts.items()}
        })
        current_summary = {
            "fused_value": fusion_out["fused_value"],
            "probability": uncertainty["probability"],
            "confidence": uncertainty["confidence"],
            "disagreement": disagreement["disagreement_level"],
            "model_forecasts": forecasts
        }
        what_changed = compute_what_changed(current_summary, prev_cycle)

        # Extreme Weather Indicator
        is_extreme = fusion_out["fused_value"] >= uncertainty["threshold"]
        severity = "RED_WARNING" if fusion_out["fused_value"] >= 115.5 else "ORANGE_ALERT" if is_extreme else "YELLOW_WATCH"

        valid_time = datetime.now(timezone.utc) + timedelta(hours=context["lead_hours"])

        return {
            "scenario_id": sc_id,
            "region_id": context["region_id"],
            "variable": context["variable"],
            "lead_hours": context["lead_hours"],
            "season": context["season"],
            "weather_regime": context["weather_regime"],
            "valid_time": valid_time.isoformat(),
            "fused_value": fusion_out["fused_value"],
            "baselines": {
                "simple_average": fusion_out["simple_average_value"],
                "static_blend": fusion_out["static_blend_value"],
                "adaptive_reliability_baseline": heuristic_fusion["fused_value"],
                "adaptive_ml_blend": fusion_out["fused_value"]
            },
            "strategy": selected_strategy,
            "weights": weights,
            "model_forecasts": forecasts,
            "disagreement": disagreement,
            "uncertainty": uncertainty,
            "explanation": explanation,
            "what_changed": what_changed,
            "extreme_guidance": {
                "event_type": "HEAVY_RAINFALL" if context["variable"] == "rainfall" else "HEATWAVE",
                "probability": uncertainty["probability"],
                "severity": severity,
                "confidence": uncertainty["confidence"],
                "threshold": uncertainty["threshold"],
                "is_active_alert": is_extreme
            },
            "data_type": scenario.get("data_type", "synthetic_demo"),
            "data_health": {
                "total_models": len(forecasts),
                "active_models": fusion_out["active_models_count"],
                "missing_models": [m for m, v in forecasts.items() if v is None],
                "injected_bias": failure_memory._injected_bias,
                "status": "OPERATIONAL" if fusion_out["active_models_count"] >= 3 else "DEGRADED_AVAILABILITY"
            }
        }

scenario_generator = ScenarioGenerator()
