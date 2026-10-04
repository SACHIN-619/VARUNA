"""
Tests for VARUNA 14-Stage Canonical Pipeline Orchestrator.
Verifies end-to-end execution, provenance tracking, and zero-fake observation handling.
"""

import pytest
from app.services.canonical_pipeline import canonical_pipeline, CanonicalPipelineOrchestrator
from app.services.data_pipeline import data_pipeline


def test_canonical_pipeline_end_to_end_execution():
    raw_forecasts = {
        "NCUM": 82.5,
        "GFS": 44.0,
        "WRF": 71.0,
        "AI_WEATHER": 69.5
    }
    
    result = canonical_pipeline.execute_pipeline(
        db=None,
        region_id="WESTERN_GHATS",
        variable="rainfall",
        lead_hours=48,
        raw_forecasts=raw_forecasts,
        observation_val=75.0
    )
    
    # Assert top-level keys
    assert result["run_id"].startswith("varuna_run_")
    assert result["region_id"] == "WESTERN_GHATS"
    assert result["variable"] == "rainfall"
    
    # Stage 2 QC
    assert result["inputs"]["harmonized_forecasts"]["NCUM"] == 82.5
    
    # Stage 5 Historical Skill Provenance
    assert result["historical_skill"]["provenance"]["NCUM"] in ["BOOTSTRAP_PRIOR", "DATABASE_VERIFIED_HISTORY"]
    
    # Stage 9 Fusion
    fused = result["fusion"].get("fused_value") or result["fusion"].get("fused_val")
    assert fused is not None
    assert 44.0 <= fused <= 82.5
    
    # Stage 10 Uncertainty
    assert "uncertainty_score" in result["uncertainty"] or "total_uncertainty" in result["uncertainty"] or "confidence_score" in result["uncertainty"]
    
    # Stage 14 Verification
    assert result["verification"]["status"] == "VERIFIED"
    assert result["verification"]["observed_value"] == 75.0
    assert "VARUNA_FUSED" in result["verification"]["forecast_errors"]


def test_canonical_pipeline_unverified_observation_safety():
    """
    Verifies that when observation_val is None, system does NOT invent fake 68.4 fallback.
    """
    raw_forecasts = {"NCUM": 50.0, "GFS": 52.0}
    
    result = canonical_pipeline.execute_pipeline(
        db=None,
        region_id="HIMALAYAN_FOOTHILLS",
        variable="rainfall",
        lead_hours=24,
        raw_forecasts=raw_forecasts,
        observation_val=None
    )
    
    assert result["verification"]["status"] == "NOT_VERIFIED" or result["verification"]["status"] == "PENDING_OBSERVATION"
    assert result["verification"]["observed_value"] is None
