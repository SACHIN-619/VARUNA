"""
VARUNA Canonical Pipeline Orchestrator.
Implements the 14-stage meteorological learning and forecasting pipeline:

 1. Ingestion           -> Receive/validate raw model forecast records
 2. Quality Control (QC)-> Perform bounds checks, unit validation, missing data flags
 3. Harmonization       -> Align grid/units (e.g. mm/day -> mm, K -> C)
 4. Context Engine      -> Identify weather regime, season, lead hours, terrain
 5. Historical Skill    -> Query DB ModelSkill / verified metrics (or BOOTSTRAP_PRIOR if cold-start)
 6. Initial Disagree.   -> Measure raw multi-model spread/variance
 7. Adaptive Trust      -> Compute model reliability weights (Heuristic + ML Meta-Trust)
 8. Weighted Disagree.  -> Measure spread weighted by model trust
 9. Forecast Fusion     -> Compute VARUNA adaptive blend + baseline comparisons
10. Uncertainty         -> Calibrate aleatoric/epistemic uncertainty & confidence score
11. Extreme Signal      -> Detect extreme events, return periods, risk alerts
12. Provenance + XAI    -> Generate run_id, audit trail, feature importance & reasoning narrative
13. Intelligence Pkg    -> Package unified forecast payload
14. Verification & Skill-> Verify against ground truth (NO fabricated defaults) & update skill memory
"""

import uuid
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.skill import ModelSkill
from app.models.verification import VerificationResult
from app.services.harmonization import harmonization_service
from app.intelligence.fusion import STATIC_WEIGHTS_DEFAULT
from app.intelligence.context_engine import context_engine
from app.intelligence.trust_model import compute_adaptive_weights
from app.intelligence.ml_trust_model import ml_trust_model
from app.intelligence.disagreement import calculate_disagreement
from app.intelligence.fusion import perform_forecast_fusion
from app.intelligence.uncertainty import compute_uncertainty_and_confidence
from app.intelligence.explainability import generate_forecast_explanation

SUPPORTED_MODELS = ["NCUM", "GFS", "WRF", "AI_WEATHER"]
CANONICAL_UNIT = {"rainfall": "mm", "temperature": "°C", "wind_speed": "m/s", "humidity": "%", "pressure": "hPa"}
# Skill rows written by real verification (as opposed to seeded illustrative priors)
QC_STALE_HOURS = 48
VERIFIED_SKILL_PERIODS = {"continuous_verification_pipeline", "LIVE_BACKFILL_ERA5", "LIVE_BACKFILL_IMD", "OPERATIONAL_VERIFICATION"}


def default_mae(model_id: str, variable: str) -> float:
    """Cold-start prior (always labelled BOOTSTRAP_PRIOR)."""
    if variable == "rainfall":
        return {"NCUM": 9.2, "GFS": 18.5, "WRF": 11.4, "AI_WEATHER": 11.8}.get(model_id, 12.0)
    if variable == "temperature":
        return 1.8
    return 2.0


def recent_verified_error(db, model_id: str, region_id: str, variable: str, lead_hours: int, n: int = 10) -> Optional[float]:
    """EMA (alpha 0.3) of the most recent verified absolute errors, oldest -> newest. None if no history."""
    try:
        rows = (db.query(VerificationResult)
                .filter(VerificationResult.model_id == model_id, VerificationResult.region_id == region_id,
                        VerificationResult.variable == variable, VerificationResult.lead_hours == lead_hours,
                        VerificationResult.metric == "MAE", VerificationResult.method == "INDIVIDUAL_MODEL")
                .order_by(VerificationResult.verification_time.desc()).limit(n).all())
    except Exception:
        return None
    if not rows:
        return None
    ema = None
    for r in reversed(rows):
        ema = r.score if ema is None else 0.3 * r.score + 0.7 * ema
    return round(float(ema), 3)


def build_lineage(models, raw, harm, weights, weights_list, fusion, unc, dis, skills, skill_prov,
                  recent, recent_prov, source_meta, strategy, unit, computed_at, extreme) -> Dict[str, Any]:
    """Explainability record for every headline number: value, formula, inputs, sources, timestamp."""
    def src(m):
        meta = source_meta.get(m, {})
        return {"model": m, "value": raw.get(m), "unit": unit, "source": meta.get("source", "SCENARIO / CALLER SUPPLIED"),
                "provenance": meta.get("provenance", "SYNTHETIC_DEMO_SCENARIO"), "dataset_id": meta.get("dataset_id"),
                "issue_time": meta.get("issue_time"), "valid_time": meta.get("valid_time"),
                "fetched_at": meta.get("fetched_at"), "url": meta.get("url")}
    terms = [{"model": m, "weight": weights.get(m, 0.0), "value": harm.get(m),
              "product": round(weights.get(m, 0.0) * harm[m], 3) if harm.get(m) is not None else None}
             for m in models]
    bias = fusion.get("bias_correction")
    w_detail = {}
    for item in weights_list:
        m = item.get("model_id")
        w_detail[m] = {
            "value": item.get("weight"), "strategy": strategy,
            "historical_mae": skills.get(m, {}).get("MAE"), "skill_provenance": skill_prov.get(m),
            "recent_error": recent.get(m), "recent_error_provenance": recent_prov.get(m),
            "predicted_error": item.get("predicted_error"), "bias_correction": item.get("bias_correction"),
            "formula": {
                "ADAPTIVE_RELIABILITY": "w_i ∝ (1/MAE_i) · 1/(1+recent_i/15) · vulnerability_i(regime, lead), normalised to sum 1",
                "ADAPTIVE_ML": "w_i = softmax(-predicted_error_i / 12); predicted_error from GBDT on 22 causal features",
                "BIAS_CORRECTED_STACK": "w = NNLS(F - bias, O) on verified history, shrunk to global fit, normalised",
            }.get(strategy, ""),
        }
    return {
        "computed_at": computed_at,
        "model_forecasts": {m: src(m) for m in models},
        "fused_value": {"value": fusion.get("fused_value"), "unit": unit,
                        "formula": "Σ w_i·(F_i − b_i)" if bias else "Σ w_i·F_i", "terms": terms, "bias_correction": bias},
        "simple_average": {"value": (fusion.get("baselines") or {}).get("simple_average"), "formula": "mean of active F_i"},
        "static_blend": {"value": (fusion.get("baselines") or {}).get("static_blend"),
                         "formula": "fixed prior weights renormalised over active models: " + ", ".join(
                             f"{m} {STATIC_WEIGHTS_DEFAULT[m]:.2f}" for m in models
                             if m in STATIC_WEIGHTS_DEFAULT and harm.get(m) is not None)},
        "weights": w_detail,
        "disagreement": {"value": dis.get("disagreement_score"), "level": dis.get("disagreement_level"),
                         "std_dev": dis.get("std_dev"), "range": dis.get("range"), "weighted_spread": dis.get("weighted_spread"),
                         "formula": "continuous score of sample std, escalated by range (variable-specific thresholds)"},
        "confidence": {"value": unc.get("confidence_score"), "level": unc.get("confidence"), **(unc.get("components") or {})},
        "probability": {"value": unc.get("probability"), "threshold": unc.get("threshold"), "calibrated": False,
                        "formula": (unc.get("components") or {}).get("probability_formula"),
                        "sigma": (unc.get("components") or {}).get("sigma")},
        "uncertainty_margin": {"value": unc.get("uncertainty_margin"), "formula": (unc.get("components") or {}).get("margin_formula")},
        "extreme_signal": {**extreme, "rule": "IMD 24 h rainfall categories / heat-wave 40 °C / gale 14 m/s"},
    }

# IMD 24h rainfall categories (mm): heavy 64.5-115.5, very heavy 115.6-204.4, extremely heavy >= 204.5
IMD_HEAVY_MM = 64.5
IMD_VERY_HEAVY_MM = 115.6
IMD_EXTREMELY_HEAVY_MM = 204.5


def compute_extreme_signal(fused_val: Optional[float], variable: str) -> Dict[str, Any]:
    """IMD-aligned extreme-event signal. Colour codes: YELLOW (heavy), ORANGE (very heavy), RED (extremely heavy)."""
    var = (variable or "rainfall").lower()
    if fused_val is None:
        return {"is_extreme": False, "category": "NO_DATA", "severity": "NO_DATA", "alert_level": "GREY",
                "threshold_exceeded": 0.0, "threshold_exceeded_mm": 0.0, "anomaly_score": 0.0}
    if var == "rainfall":
        if fused_val >= IMD_EXTREMELY_HEAVY_MM:
            cat, level = "EXTREMELY_HEAVY_RAINFALL", "RED"
        elif fused_val >= IMD_VERY_HEAVY_MM:
            cat, level = "VERY_HEAVY_RAINFALL", "ORANGE"
        elif fused_val >= IMD_HEAVY_MM:
            cat, level = "HEAVY_RAINFALL", "YELLOW"
        else:
            cat, level = "NORMAL", "GREEN"
        exceed = max(0.0, fused_val - IMD_HEAVY_MM)
        anomaly = (fused_val - 15.0) / 12.0
    elif var == "temperature":
        # IMD heatwave guidance (plains): Tmax >= 40 C; severe >= 45 C
        if fused_val >= 45.0:
            cat, level = "SEVERE_HEATWAVE", "RED"
        elif fused_val >= 40.0:
            cat, level = "HEATWAVE", "ORANGE"
        else:
            cat, level = "NORMAL", "GREEN"
        exceed = max(0.0, fused_val - 40.0)
        anomaly = (fused_val - 32.0) / 3.0
    else:  # wind_speed in m/s (canonical)
        if fused_val >= 24.5:   # ~88 km/h, storm
            cat, level = "STORM_FORCE_WIND", "RED"
        elif fused_val >= 14.0:  # ~50 km/h, gale/squall
            cat, level = "GALE_SQUALL", "ORANGE"
        else:
            cat, level = "NORMAL", "GREEN"
        exceed = max(0.0, fused_val - 14.0)
        anomaly = (fused_val - 6.0) / 3.0
    is_extreme = cat != "NORMAL"
    return {
        "is_extreme": is_extreme,
        "category": cat,
        "severity": level if is_extreme else "NORMAL",
        "alert_level": level,
        "threshold_exceeded": round(exceed, 1),
        "threshold_exceeded_mm": round(exceed, 1) if var == "rainfall" else 0.0,
        "anomaly_score": round(anomaly, 2),
    }


class CanonicalPipelineOrchestrator:
    """
    Unified 14-stage engine executing end-to-end VARUNA forecast intelligence.
    """

    def __init__(self):
        self.ml_trust = ml_trust_model

    def execute_pipeline(
        self,
        db: Optional[Session],
        region_id: str,
        variable: str,
        lead_hours: int,
        raw_forecasts: Dict[str, float],
        custom_historical_skills: Optional[Dict[str, Dict[str, float]]] = None,
        custom_recent_errors: Optional[Dict[str, float]] = None,
        observation_val: Optional[float] = None,
        run_id: Optional[str] = None,
        season: str = "SW_MONSOON",
        weather_regime: str = "HEAVY_RAINFALL",
        strategy: str = "ADAPTIVE_ML",
        source_meta: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Runs the 14 stages. The model set is whatever `raw_forecasts` contains (the classic
        NCUM/GFS/WRF/AI_WEATHER slots or live public models such as ECMWF_IFS / UKMO_UM / ICON).
        Every stage is timed and summarised in `stage_trace`; every headline number carries a
        `lineage` entry (formula, inputs, sources) so the UI can explain it on hover/click.
        """
        execution_id = run_id or f"varuna_run_{uuid.uuid4().hex[:10]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        source_meta = source_meta or {}
        models: List[str] = list(raw_forecasts.keys()) or list(SUPPORTED_MODELS)
        classic_set = set(models) <= set(SUPPORTED_MODELS)
        var = variable.lower()
        trace: List[Dict[str, Any]] = []

        def stage(no: int, key: str, name: str, status: str, t0: float, inputs: Any, outputs: Any, notes: str = ""):
            trace.append({
                "stage": no, "key": key, "name": name, "status": status,
                "duration_ms": round((time.perf_counter() - t0) * 1000, 3),
                "inputs": inputs, "outputs": outputs, "notes": notes,
            })

        # STAGE 1: INGEST
        t0 = time.perf_counter()
        present = {m: v for m, v in raw_forecasts.items() if v is not None}
        stage(1, "INGEST", "Ingest", "PASS" if present else "FAIL", t0,
              {"models_requested": models},
              {"received": list(present.keys()), "missing": [m for m in models if m not in present],
               "sources": {m: source_meta.get(m, {}).get("source", "SCENARIO / CALLER SUPPLIED") for m in models}},
              "Raw values exactly as received, before any change.")

        # STAGE 2: QUALITY CONTROL
        t0 = time.perf_counter()
        # Staleness is relative to the freshest input: inputs without an issue time (caller/scenario
        # supplied) count as "now". A whole set from one old cycle is therefore not quarantined (the
        # run's own issue time shows its age), but one old feed is never blended with fresh runs.
        def _issued(m):
            v = (source_meta.get(m) or {}).get("issue_time")
            if not v:
                return datetime.now(timezone.utc)
            try:
                t = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.now(timezone.utc)
        newest_issue = max((_issued(m) for m in models if raw_forecasts.get(m) is not None),
                           default=datetime.now(timezone.utc))
        qc_clean_forecasts: Dict[str, float] = {}
        qc_flags: Dict[str, List[str]] = {}
        for m_id in models:
            val = raw_forecasts.get(m_id)
            flags: List[str] = []
            if val is None:
                flags.append("MISSING_FEED")
            elif not isinstance(val, (int, float)) or np.isnan(val) or np.isinf(val):
                flags.append("INVALID_NUMERIC")
            else:
                if var in ["rainfall", "precip", "precipitation"] and val < 0:
                    flags.append("NEGATIVE_RAINFALL_FLAGGED")
                    val = 0.0
                elif var in ["temperature", "temp"] and (val < -90.0 or val > 60.0):
                    flags.append("EXTREME_TEMPERATURE_UNPHYSICAL")  # excluded, never blended
                    qc_flags[m_id] = flags
                    continue
                elif var in ["wind_speed", "wind"] and val < 0:
                    flags.append("NEGATIVE_WIND_FLAGGED")
                    val = 0.0
                issued = (source_meta.get(m_id) or {}).get("issue_time")
                if issued:
                    try:
                        it = datetime.fromisoformat(str(issued).replace("Z", "+00:00"))
                        if it.tzinfo is None:
                            it = it.replace(tzinfo=timezone.utc)
                        if newest_issue - it > timedelta(hours=QC_STALE_HOURS):
                            flags.append("STALE_FEED")  # quarantined: much older than the other runs being blended
                            qc_flags[m_id] = flags
                            continue
                    except ValueError:
                        pass
                qc_clean_forecasts[m_id] = float(val)
            qc_flags[m_id] = flags
        qc_state = {}
        for m_id in models:
            f = qc_flags.get(m_id, [])
            qc_state[m_id] = ("MISSING" if "MISSING_FEED" in f else "QUARANTINED" if "STALE_FEED" in f else
                              "REJECTED" if any(x in f for x in ("INVALID_NUMERIC", "EXTREME_TEMPERATURE_UNPHYSICAL")) else
                              "WARNING" if f else "ACCEPTED")
        n_flagged = sum(1 for f in qc_flags.values() if f)
        stage(2, "QC", "Quality control", "PASS" if not n_flagged else ("WARN" if qc_clean_forecasts else "FAIL"), t0,
              {"values": raw_forecasts}, {"state": qc_state, "flags": qc_flags},
              "ACCEPTED = blended; WARNING = corrected and blended (e.g. negative rain set to 0); REJECTED = unphysical, "
              f"excluded; QUARANTINED = issued > {QC_STALE_HOURS} h before the freshest input, excluded; MISSING = no value.")

        # STAGE 3: HARMONIZATION
        t0 = time.perf_counter()
        harmonized_forecasts: Dict[str, float] = {}
        for m_id, val in qc_clean_forecasts.items():
            norm_val, canonical_u, _ = harmonization_service.normalize_units(value=val, from_unit="native", target_variable=variable)
            harmonized_forecasts[m_id] = norm_val
        canonical_unit = CANONICAL_UNIT.get(var, "")
        stage(3, "HARMONIZE", "Harmonise units & ids", "PASS" if harmonized_forecasts else "FAIL", t0,
              {"unit_in": "canonical (converted at ingestion)"},
              {"unit": canonical_unit, "values": harmonized_forecasts},
              "Units are converted at ingestion (mm, °C, m/s); spatial alignment is subdivision/point extraction.")

        # STAGE 4: CONTEXT
        t0 = time.perf_counter()
        ctx_obj = context_engine.build_context(region_id=region_id, season=season, lead_hours=lead_hours,
                                               variable=variable, weather_regime=weather_regime)
        context_data = ctx_obj.model_dump() if hasattr(ctx_obj, "model_dump") else ctx_obj.dict()
        # ContextVector stores `lead_time`; every consumer reads `lead_hours`.
        context_data["lead_hours"] = context_data.get("lead_time", lead_hours)
        stage(4, "CONTEXT", "Context", "PASS", t0,
              {"region_id": region_id, "season": season, "lead_hours": lead_hours, "regime": weather_regime},
              {k: context_data.get(k) for k in ("season", "lead_time", "weather_regime", "rainfall_intensity")},
              "Regime is user-selected (not auto-detected) in this prototype.")

        # STAGE 5: HISTORICAL SKILL
        t0 = time.perf_counter()
        historical_skills: Dict[str, Dict[str, float]] = {}
        skill_provenance: Dict[str, str] = {}
        for m_id in models:
            if custom_historical_skills and m_id in custom_historical_skills:
                historical_skills[m_id] = dict(custom_historical_skills[m_id])
                skill_provenance[m_id] = "SCENARIO_PRIOR"
                continue
            db_skill = None
            if db is not None:
                base_q = db.query(ModelSkill).filter(
                    ModelSkill.model_id == m_id, ModelSkill.region_id == region_id, ModelSkill.variable == variable,
                    ModelSkill.lead_hours == lead_hours, ModelSkill.metric == "MAE")
                # Prefer verified evidence (any regime) over seeded/synthetic priors.
                db_skill = (base_q.filter(ModelSkill.evaluation_period.in_(VERIFIED_SKILL_PERIODS),
                                          ModelSkill.sample_count > 0)
                            .order_by(ModelSkill.updated_at.desc()).first()
                            or base_q.filter(ModelSkill.weather_regime == weather_regime, ModelSkill.season == season)
                            .order_by(ModelSkill.updated_at.desc()).first()
                            or base_q.order_by(ModelSkill.updated_at.desc()).first())
            if db_skill is not None and db_skill.value is not None:
                verified = (db_skill.evaluation_period or "") in VERIFIED_SKILL_PERIODS and (db_skill.sample_count or 0) > 0
                historical_skills[m_id] = {"MAE": float(db_skill.value), "sample_count": db_skill.sample_count or 0,
                                           "evaluation_period": db_skill.evaluation_period}
                skill_provenance[m_id] = "DATABASE_VERIFIED_HISTORY" if verified else "SEEDED_PRIOR"
            else:
                historical_skills[m_id] = {"MAE": default_mae(m_id, var), "sample_count": 0}
                skill_provenance[m_id] = "BOOTSTRAP_PRIOR"

        recent_error_provenance: Dict[str, str] = {}
        if custom_recent_errors:
            recent_errors = {m: custom_recent_errors.get(m, historical_skills[m]["MAE"] * 0.5) for m in models}
            recent_error_provenance = {m: "SCENARIO_PRIOR" for m in models}
        else:
            recent_errors = {}
            for m_id in models:
                ema = recent_verified_error(db, m_id, region_id, variable, lead_hours) if db is not None else None
                if ema is not None:
                    recent_errors[m_id] = ema
                    recent_error_provenance[m_id] = "VERIFIED_EMA"
                else:
                    recent_errors[m_id] = historical_skills[m_id]["MAE"] * 0.5
                    recent_error_provenance[m_id] = "PRIOR_DERIVED (0.5 x MAE)"
        stage(5, "SKILL", "Historical skill", "PASS" if any(p == "DATABASE_VERIFIED_HISTORY" for p in skill_provenance.values()) else "WARN", t0,
              {"lookup": f"{region_id} / {variable} / {lead_hours}h / {weather_regime} / {season}"},
              {"mae": {m: historical_skills[m]["MAE"] for m in models}, "provenance": skill_provenance,
               "recent_error": {m: round(v, 2) for m, v in recent_errors.items()}, "recent_error_provenance": recent_error_provenance},
              "WARN = no verified history yet for this context (priors used). Run Verify / Backfill to build real skill.")

        # STAGE 6: INITIAL DISAGREEMENT
        t0 = time.perf_counter()
        initial_disagreement = calculate_disagreement(forecasts=harmonized_forecasts, variable=variable)
        stage(6, "DISAGREEMENT", "Raw disagreement", "PASS", t0, {"values": harmonized_forecasts},
              {k: initial_disagreement.get(k) for k in ("std_dev", "range", "disagreement_score", "disagreement_level")},
              "std = sample standard deviation; score is a continuous function of std with range escalation.")

        # STAGE 7: TRUST WEIGHTS
        t0 = time.perf_counter()
        heuristic_weights_list = compute_adaptive_weights(
            model_forecasts=harmonized_forecasts, historical_skills=historical_skills, recent_errors=recent_errors,
            context=context_data, disagreement_info=initial_disagreement)
        # keep only requested models (compute_adaptive_weights iterates the dict it is given)
        heuristic_weights = {i["model_id"]: i["weight"] for i in heuristic_weights_list if "weight" in i}

        ml_weights_list: List[Dict[str, Any]] = []
        if classic_set:
            ml_weights_list = self.ml_trust.predict_weights(forecasts={m: harmonized_forecasts.get(m) for m in SUPPORTED_MODELS},
                                                            historical_skills=historical_skills, recent_errors=recent_errors,
                                                            context=context_data)
        ml_weights = {i["model_id"]: i["weight"] for i in ml_weights_list if "weight" in i}

        effective_strategy = strategy.upper()
        strategy_note = ""
        if var != "rainfall" and effective_strategy == "ADAPTIVE_ML":
            effective_strategy, strategy_note = "ADAPTIVE_RELIABILITY", "The ML meta-model is trained on rainfall only."
        stack_result = None
        if effective_strategy == "BIAS_CORRECTED_STACK":
            from app.intelligence.stacking import get_stacker_for
            stacker, stacker_src = get_stacker_for(region_id, variable, models)
            if stacker is None:
                effective_strategy, strategy_note = "ADAPTIVE_RELIABILITY", "No stacker fitted for this model set yet (run backfill)."
            else:
                stack_result = stacker.predict(harmonized_forecasts, context_data.get("weather_regime", weather_regime), lead_hours)
                stack_result["fitted_on"] = stacker_src
                n_active = sum(1 for w in stack_result["weights"].values() if w > 0)
                final_weights_list = [
                    {"model_id": m, "weight": float(w),
                     "status": ("ACTIVE" if n_active > 1 else "DEGRADED_SINGLE_SOURCE") if w > 0 else "EXCLUDED",
                     "bias_correction": stack_result["bias"].get(m)}
                    for m, w in stack_result["weights"].items()
                ]
        if effective_strategy == "ADAPTIVE_ML" and not ml_weights_list:
            effective_strategy, strategy_note = "ADAPTIVE_RELIABILITY", "ML meta-model is trained for NCUM/GFS/WRF/AI_WEATHER only."
        if effective_strategy in ("ADAPTIVE_RELIABILITY", "HEURISTIC"):
            final_weights_list = heuristic_weights_list
        elif effective_strategy == "ADAPTIVE_ML":
            final_weights_list = ml_weights_list
        final_weights = {i["model_id"]: i["weight"] for i in final_weights_list if "weight" in i}
        stage(7, "TRUST", "Adaptive trust weights", "PASS" if final_weights else "FAIL", t0,
              {"requested_strategy": strategy, "historical_mae": {m: historical_skills[m]["MAE"] for m in models}},
              {"strategy": effective_strategy, "weights": final_weights, "heuristic": heuristic_weights, "ml": ml_weights},
              strategy_note or "Weights are non-negative and sum to 1 (simplex).")

        # STAGE 8: WEIGHTED DISAGREEMENT
        t0 = time.perf_counter()
        weighted_disagreement = calculate_disagreement(forecasts=harmonized_forecasts, variable=variable, weights=final_weights_list)
        stage(8, "WEIGHTED_DISAGREEMENT", "Trust-weighted disagreement", "PASS", t0, {"weights": final_weights},
              {k: weighted_disagreement.get(k) for k in ("weighted_spread", "disagreement_level")},
              "Weighted spread = sqrt(sum w_i (F_i - F_w)^2).")

        # STAGE 9: FUSION
        t0 = time.perf_counter()
        fusion_result = perform_forecast_fusion(model_forecasts=harmonized_forecasts, weights=final_weights_list, variable=variable)
        if stack_result is not None and stack_result.get("value") is not None and fusion_result.get("fused_value") is not None:
            fusion_result["uncorrected_weighted_value"] = fusion_result["fused_value"]
            fusion_result["fused_value"] = round(stack_result["value"], 1)
            fusion_result["bias_correction"] = stack_result["bias"]
            fusion_result["stacking_cell"] = stack_result["source"]
        fused_val = fusion_result.get("fused_value")
        stage(9, "FUSION", "Fusion + baselines", "PASS" if fused_val is not None else "FAIL", t0,
              {"weights": final_weights, "values": harmonized_forecasts},
              {"fused": fused_val, "baselines": fusion_result.get("baselines"), "status": fusion_result.get("status")},
              "Fused = sum w_i F_i (stacking: sum w_i (F_i - bias_i)). Simple average and static blend are kept for comparison.")

        # STAGE 10: UNCERTAINTY
        t0 = time.perf_counter()
        uncertainty_result = compute_uncertainty_and_confidence(
            fused_value=fused_val, model_forecasts=harmonized_forecasts, weights=final_weights_list,
            disagreement_info=weighted_disagreement, context=context_data)
        stage(10, "UNCERTAINTY", "Uncertainty & confidence", "PASS" if fused_val is not None else "SKIPPED", t0,
              uncertainty_result.get("components", {}),
              {k: uncertainty_result.get(k) for k in ("confidence", "confidence_score", "probability", "uncertainty_margin")},
              "The exceedance figure is an uncalibrated indicator, not a calibrated probability.")

        # STAGE 11: EXTREME SIGNAL
        t0 = time.perf_counter()
        extreme_signal = compute_extreme_signal(fused_val, variable)
        stage(11, "EXTREME", "Extreme signal", "PASS" if fused_val is not None else "SKIPPED", t0,
              {"fused": fused_val, "variable": var}, extreme_signal,
              "IMD: heavy >= 64.5 mm (YELLOW), very heavy >= 115.6 (ORANGE), extremely heavy >= 204.5 (RED). Guidance only.")

        # STAGE 12: XAI + PROVENANCE
        t0 = time.perf_counter()
        context_data["skill_provenance"] = skill_provenance
        context_data["historical_skills"] = historical_skills
        explanation = generate_forecast_explanation(fused_value=fused_val, weights=final_weights_list,
                                                    disagreement_info=weighted_disagreement,
                                                    uncertainty_info=uncertainty_result, context=context_data)
        provenance_audit = {
            "run_id": execution_id, "timestamp": timestamp, "stages_executed": 13,
            "skill_provenance_types": skill_provenance, "pipeline_type": "CANONICAL_14_STAGE_VARUNA",
            "sources": {m: source_meta.get(m, {"source": "SCENARIO / CALLER SUPPLIED"}) for m in models},
        }
        stage(12, "XAI", "Explanation & provenance", "PASS", t0, {"dominant": explanation.get("factors", {}).get("dominant_model")},
              {"briefing_chars": len(explanation.get("text", ""))},
              "The briefing only restates computed numbers (template or optional LLM).")

        lineage = build_lineage(models, raw_forecasts, harmonized_forecasts, final_weights, final_weights_list,
                                fusion_result, uncertainty_result, weighted_disagreement, historical_skills,
                                skill_provenance, recent_errors, recent_error_provenance, source_meta,
                                effective_strategy, canonical_unit, timestamp, extreme_signal)

        # STAGE 13: PACKAGE
        t0 = time.perf_counter()
        package = {
            "run_id": execution_id,
            "timestamp": timestamp,
            "valid_time": (datetime.now(timezone.utc) + timedelta(hours=lead_hours)).isoformat(),
            "strategy": effective_strategy,
            "requested_strategy": strategy,
            "strategy_note": strategy_note,
            "region_id": region_id,
            "variable": variable,
            "lead_hours": lead_hours,
            "models": models,
            "inputs": {"raw_forecasts": raw_forecasts, "harmonized_forecasts": harmonized_forecasts, "qc_flags": qc_flags,
                       "qc_state": qc_state,
                       "source_meta": source_meta},
            "context": context_data,
            "historical_skill": {"metrics": historical_skills, "provenance": skill_provenance,
                                 "recent_errors": recent_errors, "recent_error_provenance": recent_error_provenance},
            "initial_disagreement": initial_disagreement,
            "trust_modeling": {"heuristic_trust": heuristic_weights, "ml_trust": ml_weights, "final_weights": final_weights},
            "weighted_disagreement": weighted_disagreement,
            "fusion": fusion_result,
            "uncertainty": uncertainty_result,
            "extreme_signal": extreme_signal,
            "explainability": explanation,
            "provenance": provenance_audit,
            "lineage": lineage,
            "verification": {"status": "PENDING_OBSERVATION", "verified_at": None, "observed_value": None},
        }
        stage(13, "PACKAGE", "Intelligence package", "PASS", t0, {}, {"run_id": execution_id})

        # STAGE 14: VERIFICATION & SKILL MEMORY
        t0 = time.perf_counter()
        if observation_val is not None:
            package["verification"] = self.verify_and_update_skill(
                db=db, region_id=region_id, variable=variable, lead_hours=lead_hours,
                model_forecasts=harmonized_forecasts, fused_forecast=fused_val, observation_val=observation_val)
            stage(14, "VERIFY", "Verification & skill memory", "PASS", t0, {"observed": observation_val},
                  {"errors": package["verification"].get("forecast_errors")},
                  "Errors stored as verification records; run Skill Memory update to fold them into model skill.")
        else:
            stage(14, "VERIFY", "Verification & skill memory", "PENDING", t0, {"observed": None},
                  {"status": "AWAITING_OBSERVATION"},
                  "The forecast is for the future; verify once an observation/reference exists (manual entry or ERA5).")
        package["stage_trace"] = trace
        package["provenance"]["stages_executed"] = sum(1 for t in trace if t["status"] in ("PASS", "WARN"))
        return package

    def verify_and_update_skill(
        self,
        db: Optional[Session],
        region_id: str,
        variable: str,
        lead_hours: int,
        model_forecasts: Dict[str, float],
        fused_forecast: float,
        observation_val: Optional[float]
    ) -> Dict[str, Any]:
        if observation_val is None:
            return {
                "status": "NOT_VERIFIED",
                "reason": "OBSERVATION_UNAVAILABLE",
                "observed_value": None,
                "verified_at": datetime.now(timezone.utc).isoformat()
            }

        cycle_errors = {}
        for m_id, f_val in model_forecasts.items():
            err = round(f_val - observation_val, 2)
            abs_err = round(abs(err), 2)
            cycle_errors[m_id] = {"error": err, "abs_error": abs_err}

            if db is not None:
                db.add(VerificationResult(
                    region_id=region_id,
                    variable=variable,
                    lead_hours=lead_hours,
                    model_id=m_id,
                    method="INDIVIDUAL_MODEL",
                    metric="MAE",
                    forecast_value=f_val,
                    observed_value=observation_val,
                    score=abs_err,
                    evaluation_window="canonical_pipeline",
                    verification_time=datetime.now(timezone.utc)
                ))

        fused_err = round(fused_forecast - observation_val, 2)
        fused_abs_err = round(abs(fused_err), 2)
        cycle_errors["VARUNA_FUSED"] = {"error": fused_err, "abs_error": fused_abs_err}

        if db is not None:
            db.add(VerificationResult(
                region_id=region_id,
                variable=variable,
                lead_hours=lead_hours,
                model_id=None,
                method="CANONICAL_ADAPTIVE_FUSION",
                metric="MAE",
                forecast_value=fused_forecast,
                observed_value=observation_val,
                score=fused_abs_err,
                evaluation_window="canonical_pipeline",
                verification_time=datetime.now(timezone.utc)
            ))
            db.commit()

        return {
            "status": "VERIFIED",
            "observed_value": observation_val,
            "forecast_errors": cycle_errors,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }


canonical_pipeline = CanonicalPipelineOrchestrator()
