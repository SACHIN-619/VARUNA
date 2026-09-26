import pytest
from fastapi.testclient import TestClient
import numpy as np

from app.main import app
from app.db.seed import init_db
from app.intelligence.disagreement import calculate_disagreement
from app.intelligence.trust_model import compute_adaptive_weights
from app.intelligence.fusion import perform_forecast_fusion
from app.intelligence.uncertainty import compute_uncertainty_and_confidence
from app.intelligence.failure_memory import failure_memory
from app.verification.metrics import (
    calculate_continuous_metrics,
    calculate_categorical_metrics,
    calculate_brier_score
)

# Ensure database is initialized before running tests
init_db()

# 1. Health Endpoint Test
def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "database" in data

# 2. Weather Models Registry & Historical Skill Test
def test_models_registry(client):
    response = client.get("/api/models")
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 4
    model_ids = [m["id"] for m in models]
    assert "NCUM" in model_ids
    assert "GFS" in model_ids
    assert "WRF" in model_ids
    assert "AI_WEATHER" in model_ids

def test_model_skill_endpoint(client):
    response = client.get("/api/models/NCUM/skill")
    assert response.status_code == 200
    skills = response.json()
    assert len(skills) > 0
    assert skills[0]["model_id"] == "NCUM"

# 3. Disagreement Calculation Test
def test_disagreement_spread_comparison():
    # Low disagreement test case: 10, 12, 11, 13
    low_forecasts = {"NCUM": 10.0, "WRF": 12.0, "GFS": 11.0, "AI": 13.0}
    low_res = calculate_disagreement(low_forecasts, variable="rainfall")
    assert low_res["disagreement_level"] == "LOW"
    assert low_res["std_dev"] < 5.0

    # High disagreement test case: 5, 110, 24, 85
    high_forecasts = {"NCUM": 5.0, "WRF": 110.0, "GFS": 24.0, "AI": 85.0}
    high_res = calculate_disagreement(high_forecasts, variable="rainfall")
    assert high_res["disagreement_level"] == "HIGH"
    assert high_res["std_dev"] > 40.0
    assert high_res["disagreement_score"] > low_res["disagreement_score"]

# 4. Critical Invariant: Trust Weight Sum and Bounds Test
def test_trust_weight_normalization_invariant():
    forecasts = {"NCUM": 82.0, "WRF": 47.0, "GFS": 103.0, "AI_WEATHER": 64.0}
    skills = {
        "NCUM": {"MAE": 12.0, "BIAS": 1.0},
        "WRF": {"MAE": 13.5, "BIAS": -2.0},
        "GFS": {"MAE": 22.0, "BIAS": 12.0},
        "AI_WEATHER": {"MAE": 17.5, "BIAS": -4.0}
    }
    context = {"weather_regime": "HEAVY_RAINFALL", "lead_hours": 48, "variable": "rainfall"}
    disagreement = calculate_disagreement(forecasts, "rainfall")

    weights = compute_adaptive_weights(forecasts, skills, {}, context, disagreement)
    active_weights = [w["weight"] for w in weights if w["status"] == "ACTIVE"]

    # Invariant 1: No negative weights
    for w in active_weights:
        assert w >= 0.0

    # Invariant 2: sum(weights) == 1.0 within numerical tolerance
    total_w = sum(active_weights)
    assert pytest.approx(total_w, abs=1e-4) == 1.0

# 5. Missing Model Graceful Re-normalization Test
def test_missing_model_rebalancing():
    forecasts = {"NCUM": None, "WRF": 55.0, "GFS": 92.0, "AI_WEATHER": 68.0}
    skills = {
        "NCUM": {"MAE": 12.0},
        "WRF": {"MAE": 13.5},
        "GFS": {"MAE": 22.0},
        "AI_WEATHER": {"MAE": 17.5}
    }
    context = {"weather_regime": "HEAVY_RAINFALL", "lead_hours": 48, "variable": "rainfall"}
    disagreement = calculate_disagreement(forecasts, "rainfall")

    weights = compute_adaptive_weights(forecasts, skills, {}, context, disagreement)
    
    ncum_w = next(w for w in weights if w["model_id"] == "NCUM")
    assert ncum_w["status"] == "EXCLUDED"
    assert ncum_w["weight"] == 0.0

    active_sum = sum(w["weight"] for w in weights if w["status"] == "ACTIVE")
    assert pytest.approx(active_sum, abs=1e-4) == 1.0

# 6. Deterministic Known-Value Fusion Test
def test_deterministic_weighted_fusion():
    forecasts = {"ModelA": 10.0, "ModelB": 20.0}
    weights = [
        {"model_id": "ModelA", "weight": 0.25, "status": "ACTIVE"},
        {"model_id": "ModelB", "weight": 0.75, "status": "ACTIVE"}
    ]
    res = perform_forecast_fusion(forecasts, weights, variable="rainfall")
    # Expected: 0.25*10 + 0.75*20 = 2.5 + 15 = 17.5
    assert pytest.approx(res["fused_value"], abs=1e-2) == 17.5
    assert pytest.approx(res["simple_average_value"], abs=1e-2) == 15.0

# 7. Probability vs Confidence Separation Test
def test_probability_confidence_separation():
    # Case with high value (high probability) but high disagreement (moderate/low confidence)
    forecasts = {"NCUM": 82.0, "WRF": 47.0, "GFS": 103.0, "AI_WEATHER": 64.0}
    disagreement = calculate_disagreement(forecasts, "rainfall")
    weights = [
        {"model_id": "NCUM", "weight": 0.40, "status": "ACTIVE"},
        {"model_id": "WRF", "weight": 0.30, "status": "ACTIVE"},
        {"model_id": "GFS", "weight": 0.15, "status": "ACTIVE"},
        {"model_id": "AI_WEATHER", "weight": 0.15, "status": "ACTIVE"}
    ]
    context = {"variable": "rainfall", "lead_hours": 48}
    unc = compute_uncertainty_and_confidence(70.0, forecasts, weights, disagreement, context)
    
    # Event probability is high (heavy rainfall > 64.5 mm)
    assert unc["probability"] > 50.0
    # But confidence must NOT simply equal probability; high model disagreement caps it
    assert unc["confidence"] in ["MEDIUM", "LOW"]

# 8. Verification Metrics Calculation Test
def test_verification_metrics():
    forecasts = [10.0, 20.0, 30.0, 70.0]
    observations = [12.0, 18.0, 32.0, 65.0]
    c_metrics = calculate_continuous_metrics(forecasts, observations)
    assert c_metrics["mae"] == 2.75
    assert c_metrics["bias"] == 0.75
    assert c_metrics["correlation"] > 0.95

    # Contingency table (threshold = 64.5)
    # Only index 3 has forecast >= 64.5 (70.0) and obs >= 64.5 (65.0) -> Hit=1, Miss=0, FA=0
    cat_metrics = calculate_categorical_metrics(forecasts, observations, threshold=64.5)
    assert cat_metrics["hits"] == 1
    assert cat_metrics["pod"] == 1.0
    assert cat_metrics["far"] == 0.0

    brier = calculate_brier_score([10.0, 20.0, 30.0, 80.0], observations, threshold=64.5)
    assert 0.0 <= brier <= 1.0

# 9. Failure Injection Endpoint Tests
def test_failure_injection_runtime_controls(client):
    # Inject model bias
    res_bias = client.post("/api/demo/inject-failure", json={
        "action": "simulate_model_bias",
        "model_id": "GFS",
        "bias_magnitude": 30.0
    })
    assert res_bias.status_code == 200
    data_bias = res_bias.json()
    assert data_bias["action"] == "simulate_model_bias"
    
    # Check that GFS weight is penalized
    gfs_w = next(w for w in data_bias["updated_weights"] if w["model_id"] == "GFS")
    assert gfs_w["weight"] < 0.25

    # Reset scenario
    res_reset = client.post("/api/demo/inject-failure", json={"action": "reset_scenario"})
    assert res_reset.status_code == 200
    assert res_reset.json()["action"] == "reset_scenario"

# 10. Dashboard Summary API Test
def test_dashboard_summary_endpoint(client):
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "fused_forecast" in data
    assert "baselines" in data
    assert "weights" in data
    assert "disagreement" in data
    assert "uncertainty" in data
    assert "explanation" in data
    assert "data_health" in data

# 11. Strict Temporal Split Scientific Benchmark Experiment Test
def test_temporal_split_benchmark_experiment(client):
    res = client.get("/api/verification/experiment")
    assert res.status_code == 200
    data = res.json()
    assert data["experiment_id"] == "EXP_TEMPORAL_MONSOON_BENCHMARK_2026"
    assert data["unseen_test_samples"] > 0
    assert "split_ratio" in data
    
    methods = [row["method"] for row in data["results_table"]]
    assert "SIMPLE_AVERAGE" in methods
    assert "STATIC_BLEND" in methods
    assert "ADAPTIVE_RELIABILITY_BASELINE" in methods
    assert "ADAPTIVE_ML_META_MODEL" in methods
    
    findings = data["scientific_findings"]
    assert "ml_mae_reduction_vs_simple_average_pct" in findings
    assert findings["adaptive_ml_meta_model_mae"] < findings["simple_average_mae"]

# 12. Supervised ML Meta-Model Simplex & Constraint Invariant Test
def test_ml_trust_model_simplex_invariants():
    from app.intelligence.ml_trust_model import ml_trust_model
    forecasts = {"NCUM": 80.0, "WRF": 50.0, "GFS": 105.0, "AI_WEATHER": 65.0}
    skills = {"NCUM": {"MAE": 9.0}, "WRF": {"MAE": 11.0}, "GFS": {"MAE": 20.0}, "AI_WEATHER": {"MAE": 12.0}}
    recent = {"NCUM": 2.0, "WRF": 3.0, "GFS": 15.0, "AI_WEATHER": 4.0}
    ctx = {"lead_hours": 48, "weather_regime": "HEAVY_RAINFALL", "season": "SW_MONSOON"}
    
    weights = ml_trust_model.predict_weights(forecasts, skills, recent, ctx)
    active_weights = [w["weight"] for w in weights if w["status"] == "ACTIVE"]
    
    # 1. Non-negative weights
    for w in active_weights:
        assert w >= 0.0
    # 2. Sum to 1.0 within numerical precision
    assert pytest.approx(sum(active_weights), abs=1e-4) == 1.0

# 13. Storage Provider Abstraction Test
def test_storage_provider_local():
    from app.services.storage import LocalStorageProvider
    provider = LocalStorageProvider("./data/storage_test")
    test_data = b"MOCK_METEOROLOGICAL_GRIB_OR_PARQUET_BINARY_PAYLOAD"
    
    saved_path = provider.save_bytes("test_cycle_00z.bin", test_data)
    assert provider.exists("test_cycle_00z.bin")
    retrieved = provider.get_bytes("test_cycle_00z.bin")
    assert retrieved == test_data

# 14. LLM Provider Fallback Test
def test_llm_provider_deterministic_fallback():
    from app.services.llm_provider import DeterministicTemplateProvider
    provider = DeterministicTemplateProvider()
    briefing = provider.generate_briefing({
        "region_id": "IN_TELANGANA_HYDERABAD",
        "variable": "rainfall",
        "lead_hours": 48,
        "fused_value": 72.5,
        "dominant_model": "NCUM",
        "dominant_weight_pct": 42.0,
        "probability": 75.0,
        "confidence": "MEDIUM",
        "disagreement_level": "HIGH",
        "weather_regime": "HEAVY_RAINFALL"
    })
    assert "72.5 mm" in briefing
    assert "NCUM" in briefing
    assert "MEDIUM" in briefing

