from typing import Dict, Any, List, Optional
from app.demo.scenarios import SCENARIOS
from app.services.canonical_pipeline import canonical_pipeline
from app.intelligence.failure_memory import failure_memory

# Default (non-rainfall) demo feeds. Rainfall scenarios carry mm values only; re-using them
# for temperature / wind produced physically impossible guidance (e.g. a 70 °C "heatwave").
VARIABLE_DEMO_PROFILES: Dict[str, Dict[str, Any]] = {
    "temperature": {
        "forecasts": {"NCUM": 31.4, "GFS": 32.9, "WRF": 30.6, "AI_WEATHER": 31.1},
        "historical_skills": {
            "NCUM": {"MAE": 1.2, "BIAS": 0.2}, "GFS": {"MAE": 1.9, "BIAS": 0.9},
            "WRF": {"MAE": 1.5, "BIAS": -0.4}, "AI_WEATHER": {"MAE": 1.4, "BIAS": -0.2},
        },
        "recent_errors": {"NCUM": 0.6, "GFS": 1.4, "WRF": 0.9, "AI_WEATHER": 0.8},
    },
    "wind_speed": {  # canonical unit: m/s
        "forecasts": {"NCUM": 9.6, "GFS": 11.9, "WRF": 13.4, "AI_WEATHER": 9.1},
        "historical_skills": {
            "NCUM": {"MAE": 1.6, "BIAS": 0.3}, "GFS": {"MAE": 2.4, "BIAS": 1.1},
            "WRF": {"MAE": 2.0, "BIAS": 0.8}, "AI_WEATHER": {"MAE": 1.8, "BIAS": -0.5},
        },
        "recent_errors": {"NCUM": 0.9, "GFS": 1.8, "WRF": 1.3, "AI_WEATHER": 1.1},
    },
}

REFERENCE_BASE_RAINFALL_MM = 48.0  # Telangana / Deccan climatological anchor used by the scenarios


def _region_rain_factor(region_id: Optional[str]) -> float:
    """Scales demo rainfall by the subdivision's climatological base so the region selector is meaningful."""
    if not region_id:
        return 1.0
    from app.services.harmonization import normalize_region_id
    region_id = normalize_region_id(region_id)
    try:
        from app.intelligence.spatial_weight_map import INDIAN_SUBDIVISIONS
        for sub in INDIAN_SUBDIVISIONS:
            if sub["id"] == region_id:
                return sub["physics_profile"]["base_rainfall"] / REFERENCE_BASE_RAINFALL_MM
    except Exception:
        pass
    return 1.0


def _apply_lead_spread(forecasts: Dict[str, Optional[float]], lead_hours: int) -> Dict[str, Optional[float]]:
    """Inter-model spread grows with lead time (deterministic): deviations from the mean scale by +15%/24h beyond 48h."""
    vals = [v for v in forecasts.values() if v is not None]
    if len(vals) < 2:
        return forecasts
    mean = sum(vals) / len(vals)
    k = max(0.55, 1.0 + 0.15 * (lead_hours - 48) / 24.0)
    return {m: (None if v is None else round(max(0.0, mean + (v - mean) * k), 1)) for m, v in forecasts.items()}


class ScenarioGenerator:
    """
    Demo Scenario Engine connected to the 14-stage Canonical Pipeline Orchestrator.
    Executes real-time VARUNA forecast intelligence for interactive UI demonstrations.
    """

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
        custom_context: Optional[Dict[str, Any]] = None,
        _compute_diff: bool = True
    ) -> Dict[str, Any]:
        """
        Executes the canonical 14-stage VARUNA pipeline on scenario or custom forecast feeds.
        Every context field supplied by the API (region, variable, lead, regime, season,
        strategy) is honoured — previously regime/season/strategy were silently dropped.
        """
        ctx = custom_context or {}
        sc_id = scenario_id or self.current_scenario_id
        scenario = self.get_scenario(sc_id)

        variable = (ctx.get("variable") or scenario.get("variable", "rainfall")).lower()
        lead_hours = int(ctx.get("lead_hours") or scenario.get("lead_hours", 48))
        weather_regime = (ctx.get("weather_regime") or scenario.get("weather_regime", "NORMAL")).upper()
        season = (ctx.get("season") or scenario.get("season", "SW_MONSOON")).upper()
        strategy = (ctx.get("strategy") or "ADAPTIVE_ML").upper()
        region_id = ctx.get("region_id") or scenario.get("region_id", "IN_TELANGANA_HYDERABAD")

        # 1. Inputs (variable-aware)
        if custom_forecasts:
            forecasts = dict(custom_forecasts)
            hist_skills = scenario.get("historical_skills", {}) if variable == "rainfall" else VARIABLE_DEMO_PROFILES.get(variable, {}).get("historical_skills", {})
            recent_errs = scenario.get("recent_errors", {}) if variable == "rainfall" else VARIABLE_DEMO_PROFILES.get(variable, {}).get("recent_errors", {})
        elif variable == "rainfall":
            f = _region_rain_factor(region_id)
            forecasts = {m: (None if v is None else round(v * f, 1)) for m, v in scenario["forecasts"].items()}
            forecasts = _apply_lead_spread(forecasts, lead_hours)
            hist_skills = {m: {k: (round(x * f, 2) if isinstance(x, (int, float)) else x) for k, x in sk.items()}
                           for m, sk in scenario.get("historical_skills", {}).items()}
            recent_errs = {m: round(v * f, 2) for m, v in scenario.get("recent_errors", {}).items()}
        else:
            prof = VARIABLE_DEMO_PROFILES.get(variable, VARIABLE_DEMO_PROFILES["temperature"])
            forecasts = _apply_lead_spread(dict(prof["forecasts"]), lead_hours)
            hist_skills = prof["historical_skills"]
            recent_errs = prof["recent_errors"]

        # 2. Runtime failure-injection controls (bias / dropout / forced divergence)
        for m_id in list(forecasts.keys()):
            if failure_memory.is_model_disabled(m_id):
                forecasts[m_id] = None
            elif forecasts[m_id] is not None and failure_memory.get_injected_bias(m_id) != 0.0:
                forecasts[m_id] = round(forecasts[m_id] + failure_memory.get_injected_bias(m_id), 1)
        dm = (ctx.get("disabled_model") or "").upper()
        if dm and dm in forecasts:
            forecasts[dm] = None  # per-request dropout simulation (does not touch global state)
        if failure_memory.is_forced_disagreement():
            # Documented behaviour: widen GFS upward and WRF downward
            if forecasts.get("GFS") is not None:
                forecasts["GFS"] = round(forecasts["GFS"] + (45.0 if variable == "rainfall" else 4.0), 1)
            if forecasts.get("WRF") is not None:
                forecasts["WRF"] = round(max(0.0, forecasts["WRF"] - (35.0 if variable == "rainfall" else 3.0)), 1)

        package = canonical_pipeline.execute_pipeline(
            db=None,
            region_id=region_id,
            variable=variable,
            lead_hours=lead_hours,
            raw_forecasts=forecasts,
            custom_historical_skills=hist_skills,
            custom_recent_errors=recent_errs,
            run_id=f"demo_{sc_id.lower()}",
            season=season,
            weather_regime=weather_regime,
            strategy=strategy,
        )

        # Backward compatibility aliases for legacy callers and dashboard API endpoints
        fused_val = package["fusion"].get("fused_value")
        package["weather_regime"] = package["context"].get("weather_regime", weather_regime)
        package["season"] = package["context"].get("season", season)
        package["forecasts"] = package["inputs"]["raw_forecasts"]
        package["model_forecasts"] = package["inputs"]["raw_forecasts"]
        package["fused_value"] = fused_val
        package["fused_forecast"] = fused_val
        package["confidence_score"] = package["uncertainty"].get("confidence_score", 0.0)
        package["uncertainty_score"] = round(1.0 - package["uncertainty"].get("confidence_score", 0.0), 3)
        package["disagreement"] = package["weighted_disagreement"]
        package["baselines"] = package["fusion"].get("baselines") or {
            "simple_average": package["fusion"].get("simple_average_value"),
            "static_blend": package["fusion"].get("static_blend_value"),
        }
        hist = package.get("historical_skill", {}).get("metrics", {})
        ml_items = {}
        heur_items = {}
        package["weights"] = []
        for m, w in package["trust_modeling"]["final_weights"].items():
            raw = package["inputs"]["raw_forecasts"].get(m)
            package["weights"].append({
                "model_id": m,
                "weight": float(w),
                "status": "ACTIVE" if w > 0 else ("DISABLED" if raw is None else "EXCLUDED"),
                # enriched so the UI no longer shows "Raw: N/A" / "MAE: N/A"
                "raw_forecast": raw,
                "historical_mae": hist.get(m, {}).get("MAE"),
                "historical_bias": hist.get(m, {}).get("BIAS"),
                "recent_error": (recent_errs or {}).get(m),
                "heuristic_weight": package["trust_modeling"]["heuristic_trust"].get(m),
                "ml_weight": package["trust_modeling"]["ml_trust"].get(m),
            })
        package["extreme_guidance"] = package.get("extreme_signal", {})
        package["explanation"] = package.get("explainability", {})
        package["what_changed"] = (
            self._what_changed(scenario, package, sc_id, ctx, lead_hours) if _compute_diff
            else {"summary": "diff not computed"}
        )
        active = len([v for v in forecasts.values() if v is not None])
        missing = len([v for v in forecasts.values() if v is None])
        package["data_health"] = {
            "status": "HEALTHY" if missing == 0 else ("DEGRADED" if active >= 1 else "FAILED"),
            "active_feeds": active,
            "missing_feeds": missing,
        }
        package["data_type"] = "SYNTHETIC_DEMO_SCENARIO"
        package["scenario_metadata"] = {
            "scenario_id": sc_id,
            "title": scenario["title"],
            "description": scenario["description"],
            "data_provenance": "SYNTHETIC_DEMO_SCENARIO"
        }
        return package

    def _what_changed(self, scenario, package, sc_id, ctx, lead_hours) -> Dict[str, Any]:
        """
        Cycle diff for the SAME valid time: the previous cycle (issued 24 h earlier) forecast
        this valid time at lead + 24 h. If the scenario carries an explicit previous cycle it is
        used verbatim; otherwise the previous cycle is re-computed through the same pipeline,
        so every delta shown in the UI is a computed number rather than hard-coded text.
        """
        from app.intelligence.explainability import compute_what_changed
        current = {
            "fused_value": package["fusion"].get("fused_value") or 0.0,
            "probability": package["uncertainty"].get("probability", 0.0),
            "disagreement": package["weighted_disagreement"].get("disagreement_level"),
            "confidence": package["uncertainty"].get("confidence"),
            "model_forecasts": package["inputs"]["raw_forecasts"],
        }
        prev_weights: Dict[str, float] = {}
        prev = scenario.get("previous_cycle") if package.get("variable") == "rainfall" else None
        if not prev:
            prev_ctx = dict(ctx)
            prev_ctx["lead_hours"] = min(lead_hours + 24, 72) if lead_hours < 72 else 72
            prev_pkg = self.execute_pipeline(scenario_id=sc_id, custom_context=prev_ctx, _compute_diff=False)
            if lead_hours >= 72:
                # beyond the supported 72 h horizon: inflate spread one more step for the older cycle
                prev_pkg = self.execute_pipeline(
                    scenario_id=sc_id,
                    custom_forecasts=_apply_lead_spread(dict(prev_pkg["inputs"]["raw_forecasts"]), 72),
                    custom_context=prev_ctx, _compute_diff=False)
            prev = {
                "fused_value": prev_pkg["fusion"].get("fused_value") or 0.0,
                "probability": prev_pkg["uncertainty"].get("probability", 0.0),
                "disagreement": prev_pkg["weighted_disagreement"].get("disagreement_level"),
                "confidence": prev_pkg["uncertainty"].get("confidence"),
                "model_forecasts": prev_pkg["inputs"]["raw_forecasts"],
            }
            prev_weights = dict(prev_pkg["trust_modeling"]["final_weights"])
        diff = compute_what_changed(current, prev)
        cur_weights = package["trust_modeling"]["final_weights"]
        weight_shifts = {m: round((cur_weights.get(m, 0.0) - prev_weights.get(m, 0.0)) * 100.0, 1)
                         for m in cur_weights} if prev_weights else {}
        timeline = []
        for m, dw in sorted(weight_shifts.items(), key=lambda kv: -abs(kv[1])):
            if abs(dw) >= 1.0:
                timeline.append({
                    "time": "THIS CYCLE", "type": "trust",
                    "event": f"{m} trust {'increased' if dw > 0 else 'reduced'}",
                    "detail": f"{prev_weights.get(m, 0.0) * 100:.0f}% → {cur_weights.get(m, 0.0) * 100:.0f}% ({dw:+.1f} pts)",
                })
        if diff["previous_value"] != diff["current_value"]:
            timeline.append({"time": "THIS CYCLE", "type": "fusion", "event": "Fused forecast revised",
                             "detail": f"{diff['previous_value']} → {diff['current_value']} ({diff['value_change']:+.1f})"})
        if prev.get("confidence") != current.get("confidence"):
            timeline.append({"time": "THIS CYCLE", "type": "confidence", "event": "Confidence re-graded",
                             "detail": diff["confidence_shift"]})
        diff.update({
            "fused_delta": diff["value_change"],
            "probability_shift": diff["probability_change_pct_points"],
            "confidence_change": diff["confidence_shift"],
            "disagreement_change": diff["disagreement_shift"],
            "previous_weights": prev_weights,
            "current_weights": cur_weights,
            "weight_shifts_pct_points": weight_shifts,
            "timeline": timeline,
            "comparison_basis": "SCENARIO_PREVIOUS_CYCLE" if scenario.get("previous_cycle") and package.get("variable") == "rainfall"
                                else "RECOMPUTED_PREVIOUS_CYCLE_SAME_VALID_TIME",
        })
        return diff


scenario_generator = ScenarioGenerator()
