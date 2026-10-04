"""
VARUNA Failure Recovery, Missing Source & Security Audit Test Suite.
SIH 2026 Problem Statement: SIH26081

Tests:
- Single remaining model handling (DEGRADED_SINGLE_SOURCE flag & reduced confidence)
- Zero valid models handling (FAILED_NO_SOURCES structured failure state)
- Path traversal prevention in LocalStorageProvider
- Credential leak prevention in /health and /ready endpoints
- Readiness probe subsystem validation
- Air-gapped / Grok failure graceful fallback
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.intelligence.trust_model import compute_adaptive_weights
from app.intelligence.fusion import perform_forecast_fusion
from app.intelligence.uncertainty import compute_uncertainty_and_confidence
from app.intelligence.disagreement import calculate_disagreement
from app.services.storage import LocalStorageProvider
from app.services.llm_provider import DeterministicTemplateProvider, GrokLLMProvider
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)


def test_missing_three_models_degraded_single_source():
    """
    Phase 11: If only one valid source remains, system returns forecast
    with reduced confidence and explicit status 'DEGRADED_SINGLE_SOURCE'.
    """
    # Only NCUM remains; WRF, GFS, AI are unavailable (None)
    forecasts = {"NCUM": 78.0, "WRF": None, "GFS": None, "AI_WEATHER": None}
    skills = {"NCUM": {"MAE": 9.2}}
    context = {"weather_regime": "HEAVY_RAINFALL", "lead_hours": 48, "variable": "rainfall"}
    disagreement = calculate_disagreement(forecasts, "rainfall")

    weights = compute_adaptive_weights(forecasts, skills, {}, context, disagreement)
    active_weights = [w for w in weights if w["status"] == "DEGRADED_SINGLE_SOURCE"]

    assert len(active_weights) == 1
    assert active_weights[0]["model_id"] == "NCUM"
    assert active_weights[0]["weight"] == 1.0

    fusion = perform_forecast_fusion(forecasts, weights, variable="rainfall")
    assert fusion["status"] == "DEGRADED_SINGLE_SOURCE"
    assert fusion["fused_value"] == 78.0
    assert fusion["active_models_count"] == 1

    uncertainty = compute_uncertainty_and_confidence(
        fused_value=fusion["fused_value"],
        model_forecasts=forecasts,
        weights=weights,
        disagreement_info=disagreement,
        context=context
    )
    # Epistemic confidence must be penalized when single-source
    assert uncertainty["confidence"] == "LOW"
    assert uncertainty["confidence_score"] <= 0.35


def test_zero_valid_models_structured_failure():
    """
    Phase 11: If zero valid sources remain, return a structured failure state.
    Never silently invent or hallucinate synthetic data.
    """
    all_down = {"NCUM": None, "WRF": None, "GFS": None, "AI_WEATHER": None}
    context = {"weather_regime": "HEAVY_RAINFALL", "lead_hours": 48, "variable": "rainfall"}
    disagreement = calculate_disagreement(all_down, "rainfall")

    weights = compute_adaptive_weights(all_down, {}, {}, context, disagreement)
    for w in weights:
        assert w["status"] == "FAILED_NO_SOURCES"
        assert w["weight"] == 0.0

    fusion = perform_forecast_fusion(all_down, weights, variable="rainfall")
    assert fusion["status"] == "FAILED_NO_SOURCES"
    assert fusion["fused_value"] is None
    assert fusion["active_models_count"] == 0
    assert "error_message" in fusion


def test_storage_path_traversal_prevention(tmp_path):
    """
    Phase 26 Security: Path traversal attempts must be trapped inside base_dir.
    """
    storage = LocalStorageProvider(base_dir=str(tmp_path))

    # Malicious relative paths attempting directory escape
    payload = b"sensitive meteorological configuration"
    saved_path = storage.save_bytes("../../traversal_test.bin", payload)

    # Resolved path must strictly reside within tmp_path
    saved_resolved = Path(saved_path).resolve()
    base_resolved = tmp_path.resolve()
    assert str(saved_resolved).startswith(str(base_resolved))


def test_no_credential_leak_in_health_and_ready(client):
    """
    Phase 26 Security: Public health and ready responses must never expose passwords or API keys.
    """
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    health_text = resp_health.text.lower()

    # Secret / credential tokens must not be exposed
    assert "secret_key" not in health_text
    assert "password" not in health_text
    assert "api_key" not in health_text

    resp_ready = client.get("/api/ready")
    assert resp_ready.status_code == 200
    ready_text = resp_ready.text.lower()
    assert "password" not in ready_text
    assert "secret_key" not in ready_text


def test_readiness_probe_subsystems(client):
    """
    Phase 20 Observability: /api/ready verifies all core components.
    """
    resp = client.get("/api/ready")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "READY"
    assert "subsystems" in data
    assert data["subsystems"]["database"]["status"] == "READY"
    assert data["subsystems"]["ml_meta_model"]["status"] == "READY"
    assert data["subsystems"]["storage"]["status"] == "READY"
    assert "providers" in data["subsystems"]


def test_llm_deterministic_fallback_when_grok_unconfigured():
    """
    Phase 22 Boundary: If Grok is unconfigured or disabled, deterministic template
    produces mathematically faithful explanation without error.
    """
    provider = DeterministicTemplateProvider()
    computed_facts = {
        "fused_value": 74.2,
        "variable": "rainfall",
        "region_id": "IN_TELANGANA_HYDERABAD",
        "lead_hours": 48,
        "weather_regime": "HEAVY_RAINFALL",
        "dominant_model": "NCUM",
        "dominant_weight_pct": 44.3,
        "probability": 72.4,
        "confidence": "MEDIUM",
        "disagreement_level": "HIGH"
    }
    briefing = provider.generate_briefing(computed_facts)
    assert "74.2 mm" in briefing
    assert "NCUM" in briefing
    assert "44.3%" in briefing
    assert "MEDIUM" in briefing
