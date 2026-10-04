from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.models import router as models_router
from app.api.forecasts import router as forecasts_router
from app.api.fusion import router as fusion_router
from app.api.verification import router as verification_router
from app.api.regions import router as regions_router
from app.api.extremes import router as extremes_router
from app.api.what_changed import router as what_changed_router
from app.api.dashboard import router as dashboard_router
from app.api.demo import router as demo_router
from app.api.datasets import router as datasets_router
from app.api.jobs import router as jobs_router
from app.api.experiments import router as experiments_router
from app.api.observations import router as observations_router
from app.api.live import router as live_router
from app.api.india import router as india_router
from app.api.notifications import router as notifications_router
from app.api.audit_api import router as audit_router
from app.api.governance import router as governance_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(models_router)
api_router.include_router(forecasts_router)
api_router.include_router(fusion_router)
api_router.include_router(verification_router)
api_router.include_router(observations_router)
api_router.include_router(datasets_router)
api_router.include_router(experiments_router)
api_router.include_router(jobs_router)
api_router.include_router(regions_router)
api_router.include_router(extremes_router)
api_router.include_router(what_changed_router)
api_router.include_router(dashboard_router)
api_router.include_router(demo_router)
api_router.include_router(live_router)
api_router.include_router(notifications_router)
api_router.include_router(audit_router)
api_router.include_router(governance_router)
api_router.include_router(india_router)
