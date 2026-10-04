"""
Regression tests for defects found in the October 2026 audit (see AUDIT_NOTES.md).
Each test pins a bug that previously shipped silently.
"""
import io

from app.services.canonical_pipeline import canonical_pipeline
from app.services.harmonization import harmonization_service, normalize_model_id, normalize_region_id


FEEDS = {"NCUM": 82.0, "GFS": 103.0, "WRF": 47.0, "AI_WEATHER": 64.0}


def test_pipeline_uses_real_fused_value_downstream():
    """Uncertainty / extreme signal / XAI used to be computed for fused_value = 0.0."""
    pkg = canonical_pipeline.execute_pipeline(db=None, region_id="IN_TELANGANA_DECCAN", variable="rainfall",
                                              lead_hours=48, raw_forecasts=dict(FEEDS))
    fused = pkg["fusion"]["fused_value"]
    assert fused > 60
    assert pkg["extreme_signal"]["is_extreme"] is True
    assert pkg["uncertainty"]["probability"] > 10
    assert f"{fused:.1f}" in pkg["explainability"]["text"]


def test_lead_time_reaches_uncertainty_and_context():
    """ContextVector exposes `lead_time`; consumers read `lead_hours` -> lead was always 48 h."""
    c24 = canonical_pipeline.execute_pipeline(None, "IN_TELANGANA_DECCAN", "rainfall", 24, dict(FEEDS))
    c72 = canonical_pipeline.execute_pipeline(None, "IN_TELANGANA_DECCAN", "rainfall", 72, dict(FEEDS))
    assert c24["context"]["lead_hours"] == 24 and c72["context"]["lead_hours"] == 72
    assert c24["uncertainty"]["confidence_score"] > c72["uncertainty"]["confidence_score"]


def test_weights_simplex_for_all_strategies():
    for strategy in ("ADAPTIVE_ML", "ADAPTIVE_RELIABILITY", "BIAS_CORRECTED_STACK"):
        pkg = canonical_pipeline.execute_pipeline(None, "IN_TELANGANA_DECCAN", "rainfall", 48, dict(FEEDS), strategy=strategy)
        w = pkg["trust_modeling"]["final_weights"]
        assert abs(sum(w.values()) - 1.0) < 1e-3, strategy
        assert all(v >= 0 for v in w.values())


def test_missing_model_is_excluded_from_baselines():
    feeds = dict(FEEDS, GFS=None)
    pkg = canonical_pipeline.execute_pipeline(None, "IN_TELANGANA_DECCAN", "rainfall", 48, feeds)
    assert pkg["trust_modeling"]["final_weights"]["GFS"] == 0.0
    assert pkg["fusion"]["baselines"]["simple_average"] == round((82 + 47 + 64) / 3, 1)


def test_endpoints_that_used_to_500(client):
    for path in ("/api/fusion/current", "/api/extremes"):
        r = client.get(path)
        assert r.status_code == 200, path
    ext = client.get("/api/extremes").json()["extreme_indicators"]
    temp = next(e for e in ext if e["variable"] == "temperature")
    assert temp["fused_value"] < 50  # temperature no longer re-uses rainfall mm values


def test_dashboard_honours_regime_and_dropout(client):
    d = client.get("/api/dashboard/summary?weather_regime=CONVECTIVE&disabled_model=GFS").json()
    assert d["weather_regime"] == "CONVECTIVE"
    gfs = next(w for w in d["weights"] if w["model_id"] == "GFS")
    assert gfs["weight"] == 0.0
    assert d["baselines"]["static_blend"] is not None


def test_wrong_password_is_rejected(client):
    r = client.post("/api/auth/login", data={"username": "admin@ncmrwf.gov.in", "password": "not-the-password"})
    assert r.status_code == 401


def test_ingest_requires_privileged_role(client):
    r = client.post("/api/datasets/ingest", files={"file": ("x.csv", b"model_id,variable,value\nNCUM,rainfall,1\n")})
    assert r.status_code == 401


def test_unit_and_alias_normalisation():
    assert harmonization_service.normalize_units(12.0, "mm/day", "rainfall")[1] == "mm"
    assert harmonization_service.normalize_units(25.0, "degC", "temperature")[1] == "°C"
    assert harmonization_service.normalize_units(80.0, "pct", "humidity") == (80.0, "%", False)
    assert normalize_model_id("NCUM_SYNTHETIC") == "NCUM"
    assert normalize_model_id("ai_weather_synthetic") == "AI_WEATHER"
    assert normalize_region_id("TEL") == "IN_TELANGANA_DECCAN"


def test_varuna_synth_csv_is_ingestible(db_session):
    """The project's own generator output (mm/day, degC, *_SYNTHETIC ids, short region codes)."""
    from app.services.ingestion import ingestion_engine
    csv = (
        "cycle_id,issue_date,valid_date,region_id,variable,unit,lead_hours,model_id,forecast_value\n"
        "0,2026-06-01,2026-06-02,TEL,rainfall,mm/day,24,NCUM_SYNTHETIC,12.5\n"
        "0,2026-06-01,2026-06-02,TEL,temperature,degC,24,GFS_SYNTHETIC,31.2\n"
        "0,2026-06-01,2026-06-02,TEL,wind_direction,deg,24,GFS_SYNTHETIC,210\n"
    ).encode()
    import uuid
    ds_id = f"DS_AUDIT_SYNTH_{uuid.uuid4().hex[:6]}"
    res = ingestion_engine.ingest_dataset(db_session, ds_id, csv, "s.csv", provenance="SYNTHETIC_STRESS_TEST")
    assert res["records_ingested"] == 2 and res["records_rejected"] == 1
    from app.models.canonical_record import CanonicalWeatherEntity as C
    rows = db_session.query(C).filter(C.dataset_id == ds_id).all()
    assert {r.unit for r in rows} == {"mm", "°C"}
    assert {r.model_id for r in rows} == {"NCUM", "GFS"}
    assert {r.region_id for r in rows} == {"IN_TELANGANA_DECCAN"}


def test_benchmark_does_not_mutate_production_model():
    from app.intelligence.ml_trust_model import ml_trust_model
    from app.experiments.benchmark_runner import BenchmarkExperimentRunner
    if not ml_trust_model.is_trained and not ml_trust_model.load_model():
        ml_trust_model._train_default_bootstrap_model()
    before = id(ml_trust_model.estimators["NCUM"])
    res = BenchmarkExperimentRunner(random_seed=101).run_experiment()
    assert id(ml_trust_model.estimators["NCUM"]) == before
    f = res["scientific_findings"]
    assert f["bias_corrected_stacking_mae"] < f["simple_average_mae"]
