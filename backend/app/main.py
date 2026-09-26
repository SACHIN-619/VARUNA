import sys
import os

# Auto-configure python path for backend root
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local frontends and Render URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
