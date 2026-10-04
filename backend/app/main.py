import sys
import os

# Auto-configure python path for backend root
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from contextlib import asynccontextmanager
import logging
from typing import Optional
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.db.seed import init_db
from app.api import api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
logger = logging.getLogger("varuna-blending-engine")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database schema and demo seed records exist
    logger.info("Initializing SIH26081 Forecast Intelligence Engine...")
    try:
        init_db()
        logger.info("Database schema verified and initial demo records seeded.")
    except Exception as e:
        logger.error(f"Database initialization warning: {e}")
    # Warm the ML meta-model at startup so the first user request doesn't pay
    # the ~2-4 s (re)training cost of a missing/stale bootstrap artifact.
    try:
        from app.intelligence.ml_trust_model import ml_trust_model
        if not ml_trust_model.is_trained and not ml_trust_model.load_model():
            ml_trust_model._train_default_bootstrap_model()
        logger.info("ML trust meta-model ready.")
    except Exception as e:
        logger.error(f"ML meta-model warm-up failed: {e}")
    # Restore region-fitted stackers from stored live backfill history (no network)
    try:
        from app.core.database import SessionLocal
        from app.services.live_sources import refit_stackers_from_db
        _db = SessionLocal()
        try:
            n = refit_stackers_from_db(_db)
            if n:
                logger.info(f"Restored {n} region-fitted stacker(s) from live backfill history.")
        finally:
            _db.close()
    except Exception as e:
        logger.warning(f"Stacker restore skipped: {e}")
    yield
    logger.info("Shutting down Forecast Intelligence Engine.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "### SIH26081: Hybrid AI–NWP Multi-Model Forecast Blending System\n\n"
        "**Organization:** Ministry of Earth Sciences (MoES) | **Department:** NCMRWF\n\n"
        "An intelligent meteorological decision-support platform that dynamically combines heterogeneous "
        "NWP (NCUM, GFS, WRF) and AI weather models using adaptive trust weights based on historical skill, "
        "forecast lead time, region, season, and weather regime.\n\n"
        "**Core Capabilities:**\n"
        "- **Adaptive Trust Blending:** Dynamic weights (w_i >= 0, sum(w_i) = 1.0) conditioned on regime and historical performance.\n"
        "- **Disagreement-Aware Confidence:** Epistemic uncertainty separated from event probability.\n"
        "- **Model Failure Memory:** Tracks regime vulnerabilities and handles missing/degraded models with runtime failure injection.\n"
        "- **Explainable AI (XAI):** Structured 'Why this forecast?' and 'What changed?' cycle diagnostics.\n"
        "- **Continuous Verification:** Scientific benchmark comparison against Simple Average and Static Blend baselines."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS configuration supporting development, production, and Render deployments
# Auth uses Bearer tokens (not cookies), so credentials are only enabled for an explicit
# origin allow-list. `allow_origins=["*"]` + `allow_credentials=True` is rejected by browsers.
_cors_origins = [o for o in settings.CORS_ORIGINS if o and "*" not in o]
_wildcard = (not _cors_origins) or "*" in settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _wildcard else _cors_origins,
    allow_credentials=not _wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENVIRONMENT.lower() == "production" and settings.SECRET_KEY.startswith("sih26081_super_secret_dev_key"):
    logger.warning("SECURITY: SECRET_KEY is the public development default. Set SECRET_KEY in the environment.")

# Global JSON Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled request error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred while processing the meteorological request.",
            "path": request.url.path
        }
    )

# Include API Router
app.include_router(api_router, prefix="/api")

@app.get("/api/v1/forecast/fused", tags=["Canonical API"])
def get_v1_fused_forecast(
    region_id: str = "IN_TELANGANA_HYDERABAD",
    variable: str = "rainfall",
    lead_hours: int = 48,
    weather_regime: str = "HEAVY_RAINFALL"
):
    """Canonical alias for fused forecast conforming to /api/v1 contract."""
    from app.api.forecasts import get_fused_forecast
    return get_fused_forecast(region_id=region_id, variable=variable, lead_hours=lead_hours, weather_regime=weather_regime)

@app.get("/api/forecast/intelligence", tags=["Canonical API"])
def get_forecast_intelligence_alias(
    region_id: str = "IN_TELANGANA_HYDERABAD",
    variable: str = "rainfall",
    lead_hours: int = 48,
    weather_regime: str = "HEAVY_RAINFALL",
    season: str = "SW_MONSOON",
    disabled_model: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Canonical alias for the forecast intelligence package (now backed by the database,
    so ingested datasets are actually used instead of the hard-coded demo feed)."""
    from app.services.forecast_run_service import forecast_run_service
    return forecast_run_service.create_and_execute_run(
        db=db,
        region_id=region_id,
        variable=variable,
        lead_hours=lead_hours,
        season=season,
        weather_regime=weather_regime,
        disabled_model=disabled_model
    )


@app.get("/", include_in_schema=False)
def root():
    return {
        "project": "SIH26081 Hybrid AI-NWP Forecast Blending System",
        "agency": "MoES / NCMRWF",
        "api_docs": "/api/docs",
        "health_check": "/api/health",
        "active_scenario": "Signature 48h Heavy Monsoon Rainfall (Telangana)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
