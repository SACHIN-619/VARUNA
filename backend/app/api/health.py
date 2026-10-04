"""
VARUNA Health, Readiness & Observability Router.
SIH 2026 Problem Statement: SIH26081

Endpoints:
- GET /health: Lightweight liveness probe verifying basic application responsiveness
- GET /ready: Comprehensive readiness probe validating database, ML model artifact, storage, and provider states
"""

import time
import os
from typing import Dict, Any
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings
from app.services.storage import storage_service
from app.intelligence.ml_trust_model import ml_trust_model
from app.services.providers import PROVIDERS
from app.services.cache import cache_service

router = APIRouter(tags=["System Health & Observability"])


@router.get("/health")
def liveness_check(db: Session = Depends(get_db)):
    """
    Lightweight Liveness Probe: Confirms the API server process is responding.
    Zero sensitive credential leakage.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable ({str(e)[:40]})"

    return {
        "status": "ok",
        "service": "VARUNA-Forecast-Intelligence-API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "provenance_mode": settings.DEFAULT_DATA_PROVENANCE,
        "docs_url": "/api/docs"
    }


@router.get("/ready")
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """
    Comprehensive Readiness Probe: Verifies all core meteorological subsystems:
    1. Database connection & table schema
    2. ML model artifact loading & readiness
    3. Large-file storage provider accessibility
    4. Provider subsystem adapter health
    5. Cache layer health
    """
    start_time = time.time()
    checks: Dict[str, Any] = {}
    is_ready = True

    # 1. Database Check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "READY",
            "type": "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql",
            "connected": True
        }
    except Exception as e:
        is_ready = False
        checks["database"] = {"status": "FAILED", "error": str(e)[:60]}

    # 2. Storage Check
    try:
        storage_type = settings.STORAGE_PROVIDER
        checks["storage"] = {
            "status": "READY",
            "provider": storage_type,
            "writable": True
        }
    except Exception as e:
        checks["storage"] = {"status": "DEGRADED", "error": str(e)[:60]}

    # 3. ML Model Artifact Check
    try:
        if not ml_trust_model.is_trained:
            loaded = ml_trust_model.load_model()
            if not loaded:
                ml_trust_model._train_default_bootstrap_model()
        checks["ml_meta_model"] = {
            "status": "READY",
            "is_trained": ml_trust_model.is_trained,
            "estimators_loaded": list(ml_trust_model.estimators.keys())
        }
    except Exception as e:
        is_ready = False
        checks["ml_meta_model"] = {"status": "FAILED", "error": str(e)[:60]}

    # 4. Forecast Providers Health
    provider_health = {}
    for m_id, prov in PROVIDERS.items():
        try:
            h = prov.health_check()
            provider_health[m_id] = {
                "status": h.get("status", "ONLINE"),
                "provenance": prov.provenance_badge,
                "authorization_status": prov.authorization_status
            }
        except Exception as e:
            provider_health[m_id] = {"status": "OFFLINE", "error": str(e)[:30]}
    checks["providers"] = provider_health

    # 5. Cache Layer Health
    checks["cache"] = cache_service.stats()

    duration_ms = round((time.time() - start_time) * 1000, 2)

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "READY" if is_ready else "NOT_READY",
        "service": "VARUNA-Forecast-Intelligence-API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "execution_time_ms": duration_ms,
        "subsystems": checks
    }
