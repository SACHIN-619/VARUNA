from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/health", tags=["System Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Returns deployment and operational health status.
    Ensures zero sensitive credential leaks in public responses.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable ({str(e)[:30]})"

    return {
        "status": "ok",
        "service": "SIH26081-Forecast-Intelligence-API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "provenance_mode": settings.DEFAULT_DATA_PROVENANCE,
        "docs_url": "/api/docs"
    }
