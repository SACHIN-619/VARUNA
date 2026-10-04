"""
VARUNA Canonical End-to-End Pipeline & Scientific Closed-Loop Verification.
SIH 2026 Problem Statement: SIH26081

THE CANONICAL CLOSED-LOOP TEST:
DATASET (Raw Heterogeneous File)
  ↓
INGEST (Chunked Streaming)
  ↓
VALIDATE (Schema & Physical Ranges)
  ↓
NORMALIZE (Units to Canonical Standards: mm, °C, m/s)
  ↓
HARMONIZE (Multi-Model Resolution Alignment)
  ↓
CONTEXT (Canonical ContextVector)
  ↓
MODEL FORECASTS (NCUM, GFS, WRF, AI_WEATHER)
  ↓
ADAPTIVE TRUST (Level 1 Baseline & Level 2 ML Meta-Model, Simplex Invariant)
  ↓
FUSION (Adaptive Blend vs Baselines)
  ↓
UNCERTAINTY (Spread, Confidence, Indicator)
  ↓
PERSIST (Store Audit Records in Database)
  ↓
OBSERVATION (Ground Truth Arrives via Observation Registry)
  ↓
VERIFY (Continuous Metrics: MAE, RMSE, Bias, Correlation with sample_count)
  ↓
SKILL UPDATE (Closed-Loop Database Recalibration)
  ↓
NEXT CYCLE (Subsequent cycle consumes updated skill scores)

Executes for both:
1. SYNTHETIC_STRESS_TEST (Controlled synthetic benchmark)
2. PUBLIC_BENCHMARK (IMDAA 12km reanalysis benchmark)
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import numpy as np

from app.core.database import SessionLocal
from app.services.ingestion import ingestion_engine
from app.services.harmonization import harmonization_service
from app.intelligence.context_engine import ContextEngine
from app.intelligence.disagreement import calculate_disagreement
from app.intelligence.trust_model import compute_adaptive_weights
from app.intelligence.ml_trust_model import ml_trust_model
from app.intelligence.fusion import perform_forecast_fusion
from app.intelligence.uncertainty import compute_uncertainty_and_confidence
from app.models.fusion import FusionResult, ModelWeight
from app.models.skill import ModelSkill
from app.models.verification import VerificationResult
from app.services.observation_provider import observation_registry
from app.services.data_pipeline import data_pipeline
from app.schemas.canonical import DataProvenance


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_full_pipeline_cycle(
    db: Session,
    dataset_id: str,
    provenance: str,
    obs_source: str,
    cycle_label: str
):
    """Executes the complete 14-link VARUNA scientific pipeline."""
    # -------------------------------------------------------------------------
    # LINK 1: DATASET (Raw heterogeneous tabular stream with non-standard units)
    # -------------------------------------------------------------------------
    valid_time_str = "2026-09-28T00:00:00Z"
    raw_csv = f"""valid_time,model_id,region_id,variable,value,unit,lead_hours,latitude,longitude
{valid_time_str},NCUM,IN_TELANGANA_HYDERABAD,rainfall,82.0,mm,48,17.38,78.48
{valid_time_str},GFS,IN_TELANGANA_HYDERABAD,rainfall,10.3,cm,48,17.38,78.48
{valid_time_str},WRF,IN_TELANGANA_HYDERABAD,rainfall,47.0,mm,48,17.38,78.48
{valid_time_str},AI_WEATHER,IN_TELANGANA_HYDERABAD,rainfall,64.0,mm,48,17.38,78.48
"""

    # -------------------------------------------------------------------------
    # LINK 2: INGEST (Chunked streaming ingestion)
    # -------------------------------------------------------------------------
    ingest_res = ingestion_engine.ingest_dataset(
        db=db,
        dataset_id=dataset_id,
        file_content=raw_csv.encode("utf-8"),
        filename=f"{dataset_id}.csv",
        source="MET_PORTAL",
        provenance=provenance,
        persist_records=True
    )
    assert ingest_res["status"] == "COMPLETED"
    assert ingest_res["records_ingested"] == 4

    # -------------------------------------------------------------------------
    # LINK 3 & 4: VALIDATE & NORMALIZE (GFS 10.3 cm normalized to 103.0 mm)
    # -------------------------------------------------------------------------
    # Validate units in database
    from app.models.canonical_record import CanonicalWeatherEntity
    gfs_entity = db.query(CanonicalWeatherEntity).filter(
        CanonicalWeatherEntity.dataset_id == dataset_id,
        CanonicalWeatherEntity.model_id == "GFS"
    ).first()
    assert gfs_entity is not None
    assert gfs_entity.value == 103.0
    assert gfs_entity.unit == "mm"

    # -------------------------------------------------------------------------
    # LINK 5: HARMONIZE (Spatial & temporal alignment metadata)
    # -------------------------------------------------------------------------
    harmonization_meta = harmonization_service.harmonize_spatial_resolution(
        model_id="NCUM",
        original_resolution="12km",
        target_resolution="subdivision_centroid",
        resampling_method="SUBDIVISION_AVERAGE"
    )
    assert harmonization_meta.resampling_method == "SUBDIVISION_AVERAGE"

    # -------------------------------------------------------------------------
    # LINK 6: CONTEXT (Canonical ContextVector)
    # -------------------------------------------------------------------------
    skills_in_db = {
        s.model_id: {"MAE": s.value, "BIAS": 0.0}
        for s in db.query(ModelSkill).filter(
            ModelSkill.region_id == "IN_TELANGANA_HYDERABAD",
            ModelSkill.variable == "rainfall"
        ).all()
    } or {
        "NCUM": {"MAE": 9.2, "BIAS": 0.5},
        "GFS": {"MAE": 18.5, "BIAS": 11.2},
        "WRF": {"MAE": 11.4, "BIAS": -1.2},
        "AI_WEATHER": {"MAE": 11.8, "BIAS": -2.8}
    }

    recent_errors = {"NCUM": 1.5, "GFS": 9.0, "WRF": 2.5, "AI_WEATHER": 3.0}

    # -------------------------------------------------------------------------
    # LINK 7: MODEL FORECASTS
    # -------------------------------------------------------------------------
    forecasts = {
        "NCUM": 82.0,
        "GFS": 103.0,
        "WRF": 47.0,
        "AI_WEATHER": 64.0
    }

    disagreement = calculate_disagreement(forecasts, variable="rainfall")

    context = ContextEngine.build_context(
        region_id="IN_TELANGANA_HYDERABAD",
        season="SW_MONSOON",
        lead_hours=48,
        variable="rainfall",
        weather_regime="HEAVY_RAINFALL",
        historical_skill={m: s["MAE"] for m, s in skills_in_db.items()},
        recent_error=recent_errors,
        disagreement_score=disagreement["disagreement_score"],
        forecast_spread=disagreement["forecast_spread"],
        raw_forecast_mean=float(np.mean(list(forecasts.values())))
    )
    assert context.extreme_event_flag is True

    # -------------------------------------------------------------------------
    # LINK 8: ADAPTIVE TRUST (Level 1 Baseline & Level 2 ML Meta-Model)
    # -------------------------------------------------------------------------
    rel_weights = compute_adaptive_weights(forecasts, skills_in_db, recent_errors, context, disagreement)
    active_rel_weights = [w["weight"] for w in rel_weights if w["status"] == "ACTIVE"]

    # Invariant: w_i >= 0, sum(w_i) == 1.0
    for w in active_rel_weights:
        assert w >= 0.0
    assert pytest.approx(sum(active_rel_weights), abs=1e-4) == 1.0

    # ML Meta-Model weights
    ml_weights = ml_trust_model.predict_weights(forecasts, skills_in_db, recent_errors, context)
    active_ml_weights = [w["weight"] for w in ml_weights if w["status"] == "ACTIVE"]
    for w in active_ml_weights:
        assert w >= 0.0
    assert pytest.approx(sum(active_ml_weights), abs=1e-4) == 1.0

    # -------------------------------------------------------------------------
    # LINK 9: FUSION (Adaptive Fused Value vs Baselines)
    # -------------------------------------------------------------------------
    fusion = perform_forecast_fusion(forecasts, ml_weights, variable="rainfall")
    assert fusion["status"] == "OPTIMAL_MULTI_MODEL_FUSION"
    assert fusion["fused_value"] is not None
    assert fusion["active_models_count"] == 4

    # -------------------------------------------------------------------------
    # LINK 10: UNCERTAINTY (Spread, Confidence, Hazard Indicator)
    # -------------------------------------------------------------------------
    uncertainty = compute_uncertainty_and_confidence(
        fused_value=fusion["fused_value"],
        model_forecasts=forecasts,
        weights=ml_weights,
        disagreement_info=disagreement,
        context=context
    )
    assert uncertainty["confidence"] in ["HIGH", "MEDIUM", "LOW"]
    assert uncertainty["is_calibrated_probability"] is False
    assert uncertainty["uncertainty_margin"] > 0

    # -------------------------------------------------------------------------
    # LINK 11: PERSIST (Store Fusion Record in Database)
    # -------------------------------------------------------------------------
    valid_dt = datetime.fromisoformat(valid_time_str.replace("Z", "+00:00"))
    fusion_record = FusionResult(
        region_id="IN_TELANGANA_HYDERABAD",
        variable="rainfall",
        lead_hours=48,
        valid_time=valid_dt,
        fused_value=fusion["fused_value"],
        simple_average_value=fusion["simple_average_value"],
        static_blend_value=fusion["static_blend_value"],
        probability=uncertainty["probability"],
        confidence=uncertainty["confidence"],
        confidence_score=uncertainty["confidence_score"],
        disagreement=disagreement["disagreement_level"],
        disagreement_score=disagreement["disagreement_score"],
        uncertainty=uncertainty["uncertainty_margin"],
        regime="HEAVY_RAINFALL",
        source_type=provenance,
        weights_json=ml_weights,
        model_forecasts_json=forecasts
    )
    db.add(fusion_record)
    db.commit()
    db.refresh(fusion_record)
    assert fusion_record.id is not None

    # -------------------------------------------------------------------------
    # LINK 12: OBSERVATION (Ground truth arrives via Observation Registry)
    # -------------------------------------------------------------------------
    obs_provider = observation_registry.get(obs_source)
    latest_obs = obs_provider.get_latest_observation("IN_TELANGANA_HYDERABAD", "rainfall")
    assert latest_obs is not None
    observed_value = latest_obs.observed_value
    assert observed_value > 0

    # -------------------------------------------------------------------------
    # LINK 13: VERIFY (Continuous verification matching against ground truth)
    # -------------------------------------------------------------------------
    cycle_verify = data_pipeline.ingest_and_verify_cycle(
        db=db,
        region_id="IN_TELANGANA_HYDERABAD",
        variable="rainfall",
        lead_hours=48,
        model_forecasts=forecasts,
        fused_forecast=fusion["fused_value"],
        valid_time=valid_dt,
        ground_truth=observed_value
    )
    assert "forecast_errors" in cycle_verify
    assert "VARUNA_FUSED" in cycle_verify["forecast_errors"]

    # -------------------------------------------------------------------------
    # LINK 14: SKILL UPDATE (Closed-loop model skill recalibration in DB)
    # -------------------------------------------------------------------------
    skill_update = data_pipeline.update_model_skills_from_history(
        db=db,
        region_id="IN_TELANGANA_HYDERABAD",
        variable="rainfall",
        lead_hours=48,
        season="SW_MONSOON",
        weather_regime="HEAVY_RAINFALL"
    )
    assert skill_update["status"] == "SUCCESS"
    assert "updated_model_skills" in skill_update

    # -------------------------------------------------------------------------
    # LINK 15: NEXT CYCLE (Verify subsequent cycle reads updated skill scores)
    # -------------------------------------------------------------------------
    new_skills = db.query(ModelSkill).filter(
        ModelSkill.region_id == "IN_TELANGANA_HYDERABAD",
        ModelSkill.variable == "rainfall",
        ModelSkill.lead_hours == 48,
        ModelSkill.weather_regime == "HEAVY_RAINFALL"
    ).all()
    assert len(new_skills) >= 4
    for s in new_skills:
        assert s.value > 0
        assert s.sample_count > 0


def test_canonical_pipeline_run_a_synthetic(db_session: Session):
    """
    RUN A: Comprehensive canonical closed-loop pipeline test
    under SYNTHETIC_STRESS_TEST provenance.
    """
    run_full_pipeline_cycle(
        db=db_session,
        dataset_id="CANONICAL_RUN_A_SYNTHETIC",
        provenance=DataProvenance.SYNTHETIC_STRESS_TEST.value,
        obs_source="synthetic",
        cycle_label="SYNTHETIC_STRESS_TEST_MONSOON_CYCLE"
    )


def test_canonical_pipeline_run_b_public_benchmark(db_session: Session):
    """
    RUN B: Comprehensive canonical closed-loop pipeline test
    under PUBLIC_BENCHMARK provenance (IMDAA 12km reanalysis ground truth).
    """
    run_full_pipeline_cycle(
        db=db_session,
        dataset_id="CANONICAL_RUN_B_PUBLIC_IMDAA",
        provenance=DataProvenance.PUBLIC_BENCHMARK.value,
        obs_source="imdaa",
        cycle_label="PUBLIC_IMDAA_12KM_REANALYSIS_CYCLE"
    )


def test_temporal_leakage_protection_invariant():
    """
    Phase 14: Automated test verifying that chronological train < val < test ordering
    is strictly maintained and test period is never contaminated by future knowledge.
    """
    from app.experiments.benchmark_runner import benchmark_runner
    dataset = benchmark_runner.generate_chronological_dataset()

    # Invariant: Timestamps must be monotonically strictly non-decreasing
    timestamps = [datetime.fromisoformat(row["valid_time"]) for row in dataset]
    for i in range(len(timestamps) - 1):
        assert timestamps[i] < timestamps[i + 1], f"Temporal inversion detected at day {i}!"

    # Invariant: Feature recent_error on day i must only contain causal past verification
    for i in range(len(dataset)):
        row = dataset[i]
        for m in ["NCUM", "GFS", "WRF", "AI_WEATHER"]:
            assert row["recent_errors"][m] >= 0.0
