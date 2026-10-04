"""
VARUNA Forecast Run Service & ForecastIntelligencePackage Contract Provider.
SIH 2026 Problem Statement: SIH26081

Bridges ingested datasets and raw forecast entities to the 14-Stage Canonical Pipeline Orchestrator.
Produces the canonical ForecastIntelligencePackage JSON payload consumed by the React UI.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.services.canonical_pipeline import canonical_pipeline
from app.models.canonical_record import CanonicalWeatherEntity


from app.services.harmonization import normalize_model_id  # noqa: E402


UNITS = {"rainfall": "mm", "temperature": "°C", "wind_speed": "m/s"}


def records_to_inputs(db_records) -> "tuple[Dict[str, Optional[float]], Dict[str, Dict[str, Any]]]":
    """Map stored records (one issue) to {model: value} + per-model source metadata. Reference rows are skipped."""
    inputs: Dict[str, Optional[float]] = {}
    meta: Dict[str, Dict[str, Any]] = {}
    for rec in db_records:
        canon_id = normalize_model_id(rec.model_id)
        if canon_id.startswith("OBS"):
            continue
        inputs[canon_id] = rec.value
        meta[canon_id] = {
            "source": rec.source,
            "provenance": rec.provenance,
            "dataset_id": rec.dataset_id,
            "issue_time": rec.issue_time.isoformat() + "Z" if rec.issue_time else None,
            "valid_time": rec.valid_time.isoformat() if rec.valid_time else None,
            "fetched_at": rec.created_at.isoformat() if rec.created_at else None,
            "unit": rec.unit,
            "quality_flag": rec.quality_flag,
            "grid": {"lat": rec.latitude, "lon": rec.longitude, "resolution": rec.resolution},
        }
    return inputs, meta


def load_latest_issue(db: Session, region_id: str, variable: str, lead_hours: int, provenance: Optional[str] = None):
    from sqlalchemy import func
    q = db.query(func.max(CanonicalWeatherEntity.issue_time)).filter(
        CanonicalWeatherEntity.region_id == region_id, CanonicalWeatherEntity.variable == variable,
        CanonicalWeatherEntity.lead_time == lead_hours, ~CanonicalWeatherEntity.model_id.like("OBS%"))
    if provenance:
        q = q.filter(CanonicalWeatherEntity.provenance == provenance)
    latest = q.scalar()
    if latest is None:
        return None, []
    rq = db.query(CanonicalWeatherEntity).filter(
        CanonicalWeatherEntity.region_id == region_id, CanonicalWeatherEntity.variable == variable,
        CanonicalWeatherEntity.lead_time == lead_hours, CanonicalWeatherEntity.issue_time == latest)
    if provenance:
        rq = rq.filter(CanonicalWeatherEntity.provenance == provenance)
    return latest, rq.limit(200).all()


PROVENANCE_PRIORITY = {"AUTHORIZED_OPERATIONAL_FEED": 0, "PUBLIC_API_FORECAST": 1}


def load_merged_fresh(db: Session, region_id: str, variable: str, lead_hours: int, max_age_hours: int = 36):
    """
    India-first merge for one valid day: every model's freshest record from the last `max_age_hours`,
    preferring authorised Indian feeds (NCMRWF / IMD files) over global public APIs for the same slot.
    Returns (latest_issue, records) or (None, []).
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=max_age_hours)
    recs = (db.query(CanonicalWeatherEntity)
            .filter(CanonicalWeatherEntity.region_id == region_id, CanonicalWeatherEntity.variable == variable,
                    CanonicalWeatherEntity.lead_time == lead_hours, CanonicalWeatherEntity.issue_time >= cutoff,
                    CanonicalWeatherEntity.provenance.in_(list(PROVENANCE_PRIORITY)),
                    ~CanonicalWeatherEntity.model_id.like("OBS%"))
            .order_by(CanonicalWeatherEntity.issue_time.desc()).limit(500).all())
    if not recs:
        return None, []
    target_valid = recs[0].valid_time
    best: Dict[str, Any] = {}
    for r in recs:
        if r.valid_time != target_valid:
            continue
        slot = normalize_model_id(r.model_id)
        key = (PROVENANCE_PRIORITY.get(r.provenance, 9), -r.issue_time.timestamp())
        if slot not in best or key < best[slot][0]:
            best[slot] = (key, r)
    chosen = [v[1] for v in best.values()]
    return max(r.issue_time for r in chosen), chosen


def enrich_for_dashboard(package: Dict[str, Any]) -> Dict[str, Any]:
    """Adds the flat fields the control-room UI reads (same shape as the demo scenario generator)."""
    fused = package["fusion"].get("fused_value")
    package["weather_regime"] = package["context"].get("weather_regime")
    package["season"] = package["context"].get("season")
    package["forecasts"] = package["model_forecasts"] = package["inputs"]["raw_forecasts"]
    package["fused_value"] = package["fused_forecast"] = fused
    package["confidence_score"] = package["uncertainty"].get("confidence_score", 0.0)
    package["disagreement"] = package["weighted_disagreement"]
    package["baselines"] = package["fusion"].get("baselines") or {
        "simple_average": package["fusion"].get("simple_average_value"),
        "static_blend": package["fusion"].get("static_blend_value")}
    hist = package["historical_skill"]["metrics"]
    rec = package["historical_skill"].get("recent_errors", {})
    package["weights"] = []
    for m, w in package["trust_modeling"]["final_weights"].items():
        raw = package["inputs"]["raw_forecasts"].get(m)
        package["weights"].append({
            "model_id": m, "weight": float(w),
            "status": "ACTIVE" if w > 0 else ("DISABLED" if raw is None else "EXCLUDED"),
            "raw_forecast": raw, "historical_mae": hist.get(m, {}).get("MAE"),
            "historical_bias": hist.get(m, {}).get("BIAS"), "recent_error": rec.get(m),
            "heuristic_weight": package["trust_modeling"]["heuristic_trust"].get(m),
            "ml_weight": package["trust_modeling"]["ml_trust"].get(m),
            "skill_provenance": package["historical_skill"]["provenance"].get(m),
        })
    package["extreme_guidance"] = package.get("extreme_signal", {})
    package["explanation"] = package.get("explainability", {})
    vals = package["inputs"]["raw_forecasts"]
    active = sum(1 for v in vals.values() if v is not None)
    package["data_health"] = {"status": "HEALTHY" if active == len(vals) else ("DEGRADED" if active else "FAILED"),
                              "active_feeds": active, "missing_feeds": len(vals) - active}
    return package


class CyclePayload(BaseModel):
    run_id: str
    issue_time: str
    valid_time: str
    lead_hours: int
    region_id: str
    variable: str
    season: str
    weather_regime: str


class ProvenancePayload(BaseModel):
    overall_status: str = "CANONICAL_14_STAGE_EXECUTION"
    source_type: str = "HYBRID_NWP_AI_FUSION"
    dataset_ids: List[str] = Field(default_factory=lambda: ["IMDAA_REANALYSIS", "NCMRWF_OPERATIONAL"])
    model_sources: List[str] = Field(default_factory=lambda: ["NCUM", "GFS", "WRF", "AI_WEATHER"])
    observation_status: str = "PENDING_OBSERVATION"
    evidence_status: str = "BOOTSTRAP_PRIOR"


class SourceForecastItem(BaseModel):
    model_id: str
    value: Optional[float] = None
    unit: str = "mm"
    status: str = "ACTIVE"
    provenance: str = "AUTHORIZED_PROVIDER"


class TrustItem(BaseModel):
    model_id: str
    weight: float
    skill_evidence: float = 80.0
    recent_error_evidence: float = 75.0
    lead_time_evidence: float = 80.0
    regime_evidence: float = 85.0
    disagreement_penalty: float = 10.0
    availability: float = 100.0
    evidence_status: str = "BOOTSTRAP_PRIOR"


class FusionPayload(BaseModel):
    fused_value: Optional[float] = None
    unit: str = "mm"
    strategy: str = "ADAPTIVE_ML_FUSION"
    baseline_comparisons: Dict[str, Optional[float]]


class VerificationPayload(BaseModel):
    status: str = "PENDING_OBSERVATION"
    observation_available: bool = False
    metrics: Dict[str, Any] = Field(default_factory=dict)
    sample_count: int = 0
    evaluation_window: str = "canonical_pipeline"
    provenance: str = "PENDING_OBSERVATION"


class PipelineStageItem(BaseModel):
    name: str
    status: str = "PASS"
    details: Optional[str] = None


class AuditPayload(BaseModel):
    pipeline_stages: List[PipelineStageItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    failed_checks: List[str] = Field(default_factory=list)


class ForecastIntelligencePackage(BaseModel):
    """
    Canonical API Contract consumed by React Control Room, Fusion Centre,
    Model Trust Map, and XAI screens.
    """
    cycle: CyclePayload
    provenance: ProvenancePayload
    forecasts: List[SourceForecastItem]
    trust: List[TrustItem]
    fusion: FusionPayload
    disagreement: Dict[str, Any]
    uncertainty: Dict[str, Any]
    extreme_signal: Dict[str, Any]
    explanation: Dict[str, Any]
    verification: VerificationPayload
    data_health: Dict[str, Any]
    audit: AuditPayload

    # Flat top-level backward compatibility fields for legacy endpoints
    active_cycle: str
    region_id: str
    variable: str
    lead_hours: int
    weather_regime: str
    season: str
    fused_forecast: Optional[float] = None
    fused_value: Optional[float] = None
    unit: str
    baselines: Dict[str, Optional[float]]
    model_forecasts: Dict[str, Optional[float]]
    weights: List[Dict[str, Any]]
    extreme_guidance: Dict[str, Any]
    what_changed: Dict[str, Any]
    data_type: str


class ForecastRunService:
    """Coordinates forecast execution and builds the unified ForecastIntelligencePackage payload."""

    def __init__(self):
        self.orchestrator = canonical_pipeline

    def create_and_execute_run(
        self,
        db: Optional[Session],
        region_id: str = "IN_TELANGANA_HYDERABAD",
        variable: str = "rainfall",
        lead_hours: int = 48,
        season: str = "SW_MONSOON",
        weather_regime: str = "HEAVY_RAINFALL",
        raw_forecasts: Optional[Dict[str, float]] = None,
        ground_truth: Optional[float] = None,
        disabled_model: Optional[str] = None
    ) -> ForecastIntelligencePackage:
        from app.services.harmonization import normalize_region_id
        region_id = normalize_region_id(region_id)
        active_dataset_ids = []
        is_synthetic_fallback = False
        source_meta: Dict[str, Dict[str, Any]] = {}

        if raw_forecasts:
            forecast_inputs = raw_forecasts
            active_dataset_ids = ["USER_SUPPLIED_INGESTION"]
        elif db is not None:
            # Latest issued value per model for this (region, variable, lead).
            # Previously `.all()` loaded every historical row into memory and the dict
            # comprehension kept an arbitrary (last-scanned) value per model.
            from sqlalchemy import func
            latest_issue = (
                db.query(func.max(CanonicalWeatherEntity.issue_time))
                .filter(
                    CanonicalWeatherEntity.region_id == region_id,
                    CanonicalWeatherEntity.variable == variable,
                    CanonicalWeatherEntity.lead_time == lead_hours,
                )
                .scalar()
            )
            db_records = []
            if latest_issue is not None:
                db_records = (
                    db.query(CanonicalWeatherEntity)
                    .filter(
                        CanonicalWeatherEntity.region_id == region_id,
                        CanonicalWeatherEntity.variable == variable,
                        CanonicalWeatherEntity.lead_time == lead_hours,
                        CanonicalWeatherEntity.issue_time == latest_issue,
                    )
                    .limit(200)
                    .all()
                )
            forecast_inputs, source_meta = records_to_inputs(db_records)
            if forecast_inputs:
                active_dataset_ids = list(set(rec.dataset_id for rec in db_records if rec.dataset_id))
            else:
                forecast_inputs = {
                    "NCUM": 82.0,
                    "GFS": 103.0,
                    "WRF": 47.0,
                    "AI_WEATHER": 64.0
                }
                active_dataset_ids = ["SYNTHETIC_STRESS_TEST"]
                is_synthetic_fallback = True
        else:
            forecast_inputs = {
                "NCUM": 82.0,
                "GFS": 103.0,
                "WRF": 47.0,
                "AI_WEATHER": 64.0
            }
            active_dataset_ids = ["SYNTHETIC_STRESS_TEST"]
            is_synthetic_fallback = True

        forecast_inputs = dict(forecast_inputs)
        if disabled_model and disabled_model in forecast_inputs:
            forecast_inputs[disabled_model] = None

        raw_res = self.orchestrator.execute_pipeline(
            db=db,
            region_id=region_id,
            variable=variable,
            lead_hours=lead_hours,
            raw_forecasts=forecast_inputs,
            season=season,
            weather_regime=weather_regime,
            observation_val=ground_truth,
            source_meta=source_meta,
        )

        unit_label = "mm" if variable == "rainfall" else "°C" if variable == "temperature" else "m/s"
        now_utc = datetime.now(timezone.utc)
        issue_iso = now_utc.isoformat()
        valid_iso = (now_utc + timedelta(hours=lead_hours)).isoformat()

        # Build nested payloads
        cycle = CyclePayload(
            run_id=raw_res["run_id"],
            issue_time=issue_iso,
            valid_time=valid_iso,
            lead_hours=lead_hours,
            region_id=region_id,
            variable=variable,
            season=raw_res.get("season", season),
            weather_regime=raw_res.get("weather_regime", weather_regime)
        )

        provenance = ProvenancePayload(
            overall_status=raw_res.get("provenance", {}).get("pipeline_type", "CANONICAL_14_STAGE_VARUNA"),
            source_type="SYNTHETIC_DEMO_FIXTURE" if is_synthetic_fallback else "HYBRID_NWP_AI_FUSION",
            dataset_ids=active_dataset_ids,
            model_sources=list(forecast_inputs.keys()),
            observation_status=raw_res.get("verification", {}).get("status", "PENDING_OBSERVATION"),
            evidence_status="SYNTHETIC_STRESS_TEST" if is_synthetic_fallback else ("DATABASE_VERIFIED" if any(
                p != "BOOTSTRAP_PRIOR"
                for p in raw_res.get("historical_skill", {}).get("provenance", {}).values()
            ) else "BOOTSTRAP_PRIOR")
        )

        sources = [
            SourceForecastItem(
                model_id=m_id,
                value=val,
                unit=unit_label,
                status="DISABLED" if val is None else "ACTIVE",
                provenance="SYNTHETIC_STRESS_TEST" if is_synthetic_fallback else raw_res.get("historical_skill", {}).get("provenance", {}).get(m_id, "BOOTSTRAP_PRIOR")
            )
            for m_id, val in forecast_inputs.items()
        ]

        # Extract weights dict safely from either scenario_generator or canonical_pipeline response
        raw_weights = raw_res.get("weights")
        if isinstance(raw_weights, list):
            weights_list = raw_weights
        else:
            final_w_dict = raw_res.get("trust_modeling", {}).get("final_weights", {})
            if not final_w_dict and isinstance(raw_res.get("weights"), dict):
                final_w_dict = raw_res["weights"]
            hist_metrics = raw_res.get("historical_skill", {}).get("metrics", {})
            weights_list = [
                {
                    "model_id": m_id,
                    "weight": w_val,
                    "historical_mae": hist_metrics.get(m_id, {}).get("MAE"),
                    "status": "ACTIVE" if w_val > 0 else "EXCLUDED",
                }
                for m_id, w_val in final_w_dict.items()
            ]

        disagree_dict = raw_res.get("disagreement") or raw_res.get("weighted_disagreement") or raw_res.get("initial_disagreement") or {}

        # Evidence scores are derived from the actual run inputs (previously constants 75/80/85).
        hist_metrics = raw_res.get("historical_skill", {}).get("metrics", {})
        ctx = raw_res.get("context", {}) or {}
        recent_err_map = ctx.get("recent_error", {}) or {}
        maes = [v.get("MAE") for v in hist_metrics.values() if v.get("MAE")]
        best_mae = min(maes) if maes else None
        from app.intelligence.failure_memory import failure_memory as _fm
        trust_items = []
        for w_item in weights_list:
            m_id = w_item["model_id"]
            mae = hist_metrics.get(m_id, {}).get("MAE")
            rec = recent_err_map.get(m_id)
            vuln = _fm.evaluate_historical_vulnerability(
                m_id, raw_res.get("weather_regime", weather_regime), lead_hours, raw_res.get("season", season)
            )["vulnerability_multiplier"]
            trust_items.append(TrustItem(
                model_id=m_id,
                weight=w_item["weight"],
                skill_evidence=round(100.0 * best_mae / mae, 1) if (mae and best_mae) else 0.0,
                recent_error_evidence=round(100.0 / (1.0 + max(0.0, rec or 0.0) / 15.0), 1) if rec is not None else 0.0,
                lead_time_evidence=round(max(0.0, 100.0 - max(0, lead_hours - 24) * 0.5), 1),
                regime_evidence=round(min(100.0, 85.0 * vuln), 1),
                disagreement_penalty=round(disagree_dict.get("disagreement_score", 0.0) * 100.0, 1),
                availability=0.0 if w_item.get("status") == "EXCLUDED" else 100.0,
                evidence_status="SYNTHETIC_STRESS_TEST" if is_synthetic_fallback else (
                    raw_res.get("historical_skill", {}).get("provenance", {}).get(m_id, "BOOTSTRAP_PRIOR"))
            ))

        fusion_dict = raw_res.get("fusion", {})
        baselines_dict = fusion_dict.get("baselines") or {
            "simple_average": fusion_dict.get("simple_average_value", 0.0),
            "static_blend": fusion_dict.get("static_blend_value", 0.0)
        }

        fusion = FusionPayload(
            fused_value=fusion_dict.get("fused_value", 0.0) or 0.0,
            unit=unit_label,
            strategy="ADAPTIVE_ML_FUSION",
            baseline_comparisons=baselines_dict
        )

        verification = VerificationPayload(
            status=raw_res.get("verification", {}).get("status", "PENDING_OBSERVATION"),
            observation_available=raw_res.get("verification", {}).get("observed_value") is not None,
            metrics=raw_res.get("verification", {}).get("forecast_errors", {}),
            sample_count=1 if raw_res.get("verification", {}).get("observed_value") is not None else 0,
            evaluation_window="canonical_pipeline",
            provenance="VERIFIED_OBSERVATION" if raw_res.get("verification", {}).get("observed_value") is not None else "PENDING_OBSERVATION"
        )

        default_stages = [
            PipelineStageItem(name=t["name"], status=t["status"], details=t.get("notes") or "")
            for t in raw_res.get("stage_trace", [])
        ]

        audit = AuditPayload(
            pipeline_stages=default_stages,
            warnings=[t["notes"] for t in raw_res.get("stage_trace", []) if t["status"] == "WARN" and t.get("notes")],
            failed_checks=[t["name"] for t in raw_res.get("stage_trace", []) if t["status"] == "FAIL"]
        )

        fused_val = fusion.fused_value

        return ForecastIntelligencePackage(
            cycle=cycle,
            provenance=provenance,
            forecasts=sources,
            trust=trust_items,
            fusion=fusion,
            disagreement=disagree_dict,
            uncertainty=raw_res.get("uncertainty", {}),
            extreme_signal=raw_res.get("extreme_signal", {}),
            explanation=raw_res.get("explanation") or raw_res.get("explainability", {}),
            verification=verification,
            data_health=raw_res.get("data_health", {"status": "HEALTHY", "available_sources": 4, "total_sources": 4}),
            audit=audit,

            # Legacy top-level properties
            active_cycle=issue_iso,
            region_id=region_id,
            variable=variable,
            lead_hours=lead_hours,
            weather_regime=raw_res.get("weather_regime", weather_regime),
            season=raw_res.get("season", season),
            fused_forecast=fused_val,
            fused_value=fused_val,
            unit=unit_label,
            baselines=baselines_dict,
            model_forecasts=forecast_inputs,
            weights=weights_list,
            extreme_guidance=raw_res.get("extreme_signal", {}),
            what_changed=raw_res.get("what_changed", {"primary_driver": "Canonical 14-Stage Adaptive ML Fusion"}),
            data_type="CANONICAL_14_STAGE_VARUNA"
        )

    def run_from_database(self, db: Session, region_id: str, variable: str, lead_hours: int, season: str,
                          weather_regime: str, strategy: str = "ADAPTIVE_ML", provenance: Optional[str] = None,
                          disabled_model: Optional[str] = None, merge_fresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Pipeline over stored forecasts. merge_fresh=True: India-first merge of fresh authorised + public records
        for one valid day; otherwise the latest stored issue (optionally of one provenance). None if nothing stored.
        """
        from app.services.harmonization import normalize_region_id
        region_id = normalize_region_id(region_id)
        if merge_fresh:
            latest, recs = load_merged_fresh(db, region_id, variable, lead_hours)
        else:
            latest, recs = load_latest_issue(db, region_id, variable, lead_hours, provenance)
        inputs, meta = records_to_inputs(recs)
        if not inputs:
            return None
        if disabled_model and disabled_model.upper() in inputs:
            inputs[disabled_model.upper()] = None
        pkg = self.orchestrator.execute_pipeline(
            db=db, region_id=region_id, variable=variable, lead_hours=lead_hours, raw_forecasts=inputs,
            season=season, weather_regime=weather_regime, strategy=strategy, source_meta=meta,
            run_id=f"db_{region_id}_{variable}_{lead_hours}_{latest.strftime('%Y%m%dT%H')}")
        pkg = enrich_for_dashboard(pkg)
        provs = {m.get("provenance") for m in meta.values()}
        pkg["data_type"] = ("PUBLIC_API_FORECAST" if provs == {"PUBLIC_API_FORECAST"} else
                            "INDIA_OPERATIONAL" if provs == {"AUTHORIZED_OPERATIONAL_FEED"} else
                            "INDIA_OPERATIONAL+GLOBAL_REFERENCE" if provs == {"AUTHORIZED_OPERATIONAL_FEED", "PUBLIC_API_FORECAST"} else
                            next(iter(provs)) if len(provs) == 1 else "MIXED_SOURCES")
        pkg["issue_time"] = latest.isoformat() + "Z"
        pkg["dataset_ids"] = sorted({m.get("dataset_id") for m in meta.values() if m.get("dataset_id")})
        pkg["what_changed"] = self._diff_previous_issue(db, region_id, variable, lead_hours, latest, pkg,
                                                        None if merge_fresh else provenance)
        return pkg

    def _diff_previous_issue(self, db, region_id, variable, lead_hours, latest, pkg, provenance) -> Dict[str, Any]:
        """Compare with the previous stored issue for the same valid day (lead + 24 h one issue earlier)."""
        from sqlalchemy import func
        valid = None
        for m in (pkg["inputs"].get("source_meta") or {}).values():
            valid = m.get("valid_time")
            break
        if not valid:
            return {"summary": "No previous issue to compare with.", "comparison_basis": "NONE"}
        q = db.query(CanonicalWeatherEntity).filter(
            CanonicalWeatherEntity.region_id == region_id, CanonicalWeatherEntity.variable == variable,
            CanonicalWeatherEntity.valid_time == datetime.fromisoformat(valid), CanonicalWeatherEntity.issue_time < latest,
            ~CanonicalWeatherEntity.model_id.like("OBS%"))
        if provenance:
            q = q.filter(CanonicalWeatherEntity.provenance == provenance)
        prev_issue = q.with_entities(func.max(CanonicalWeatherEntity.issue_time)).scalar()
        if prev_issue is None:
            return {"summary": "First stored issue for this valid day - nothing to compare yet.",
                    "comparison_basis": "NONE", "timeline": []}
        prev_recs = q.filter(CanonicalWeatherEntity.issue_time == prev_issue).all()
        prev_inputs, prev_meta = records_to_inputs(prev_recs)
        prev_lead = prev_recs[0].lead_time if prev_recs else lead_hours
        prev_pkg = self.orchestrator.execute_pipeline(
            db=db, region_id=region_id, variable=variable, lead_hours=prev_lead, raw_forecasts=prev_inputs,
            season=pkg.get("season") or "SW_MONSOON", weather_regime=pkg.get("weather_regime") or "NORMAL",
            strategy=pkg.get("requested_strategy", "ADAPTIVE_ML"), source_meta=prev_meta)
        from app.intelligence.explainability import compute_what_changed
        cur = {"fused_value": pkg["fusion"].get("fused_value") or 0.0, "probability": pkg["uncertainty"].get("probability", 0.0),
               "disagreement": pkg["weighted_disagreement"].get("disagreement_level"),
               "confidence": pkg["uncertainty"].get("confidence"), "model_forecasts": pkg["inputs"]["raw_forecasts"]}
        prev = {"fused_value": prev_pkg["fusion"].get("fused_value") or 0.0,
                "probability": prev_pkg["uncertainty"].get("probability", 0.0),
                "disagreement": prev_pkg["weighted_disagreement"].get("disagreement_level"),
                "confidence": prev_pkg["uncertainty"].get("confidence"), "model_forecasts": prev_inputs}
        diff = compute_what_changed(cur, prev)
        cw, pw = pkg["trust_modeling"]["final_weights"], prev_pkg["trust_modeling"]["final_weights"]
        shifts = {m: round((cw.get(m, 0.0) - pw.get(m, 0.0)) * 100.0, 1) for m in set(cw) | set(pw)}
        diff.update({
            "fused_delta": diff["value_change"], "probability_shift": diff["probability_change_pct_points"],
            "confidence_change": diff["confidence_shift"], "disagreement_change": diff["disagreement_shift"],
            "previous_weights": pw, "current_weights": cw, "weight_shifts_pct_points": shifts,
            "previous_issue_time": prev_issue.isoformat() + "Z", "current_issue_time": latest.isoformat() + "Z",
            "comparison_basis": "STORED_PREVIOUS_ISSUE_SAME_VALID_DAY",
            "timeline": [{"time": prev_issue.isoformat() + "Z", "type": "issue", "event": "Previous issue",
                          "detail": f"fused {prev['fused_value']}"},
                         {"time": latest.isoformat() + "Z", "type": "issue", "event": "Current issue",
                          "detail": f"fused {cur['fused_value']}"}],
        })
        return diff


forecast_run_service = ForecastRunService()

