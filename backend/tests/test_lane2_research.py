"""
VARUNA Lane 2 — Scientific Research Pipeline Unit & Integration Tests.
SIH 2026 Problem Statement: SIH26081
"""

import pytest
from app.services.real_datasets import real_dataset_repository, SUBDIVISION_METADATA
from app.intelligence.ml_trust_model import ml_trust_model
from app.experiments.benchmark_runner import BenchmarkExperimentRunner
from app.schemas.canonical import DataProvenance


def test_real_dataset_repository_loading():
    """Verify that Lane 2 real open dataset repository returns structured monsoon historical records."""
    dataset = real_dataset_repository.load_historical_monsoon_benchmark(
        start_date="2024-06-01",
        end_date="2024-06-10"
    )

    assert len(dataset) > 0
    sample = dataset[0]

    assert "record_id" in sample
    assert "valid_time" in sample
    assert "region_id" in sample
    assert sample["region_id"] in SUBDIVISION_METADATA
    assert "ground_truth_obs" in sample
    assert "forecasts" in sample
    assert "NCUM" in sample["forecasts"]
    assert "GFS" in sample["forecasts"]
    assert "WRF" in sample["forecasts"]
    assert "AI_WEATHER" in sample["forecasts"]
    assert "actual_errors" in sample
    assert sample["provenance"] in [DataProvenance.SYNTHETIC_STRESS_TEST.value, DataProvenance.PUBLIC_BENCHMARK.value]



def test_ml_meta_model_fit_on_real_records():
    """Verify that MLTrustMetaModel fits cleanly on real historical records."""
    records = real_dataset_repository.load_historical_monsoon_benchmark(
        start_date="2024-06-01",
        end_date="2024-06-15"
    )

    ml_trust_model.fit_on_real_records(records)
    assert ml_trust_model.is_trained is True

    # Test weight prediction
    sample = records[0]
    weights = ml_trust_model.predict_weights(
        forecasts=sample["forecasts"],
        historical_skills={m: {"MAE": 8.0, "BIAS": 0.0} for m in ["NCUM", "GFS", "WRF", "AI_WEATHER"]},
        recent_errors={m: 5.0 for m in ["NCUM", "GFS", "WRF", "AI_WEATHER"]},
        context={"lead_hours": 48, "weather_regime": "HEAVY_RAINFALL", "season": "SW_MONSOON"}
    )

    assert len(weights) == 4
    total_w = sum(w["weight"] for w in weights)
    assert pytest.approx(total_w, abs=1e-4) == 1.0


def test_benchmark_runner_lane2_research():
    """Verify that BenchmarkExperimentRunner executes Lane 2 research evaluation cleanly."""
    runner = BenchmarkExperimentRunner(lane="research")
    assert runner.provenance == DataProvenance.PUBLIC_BENCHMARK.value

    results = runner.run_experiment()
    assert results is not None
    assert "results_table" in results
    assert "scientific_findings" in results

    # Verify ML meta-model outperforms simple average on unseen test split
    ml_mae = results["scientific_findings"]["adaptive_ml_meta_model_mae"]
    simple_avg_mae = results["scientific_findings"]["simple_average_mae"]

    assert ml_mae <= simple_avg_mae
    assert results["scientific_findings"]["ml_mae_reduction_vs_simple_average_pct"] > 0
