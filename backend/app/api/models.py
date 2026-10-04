from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.weather_model import WeatherModel
from app.models.skill import ModelSkill
from app.schemas.all_schemas import WeatherModelResponse, ModelSkillResponse

router = APIRouter(prefix="/models", tags=["Weather Models Registry"])

@router.get("", response_model=List[WeatherModelResponse])
def list_weather_models(db: Session = Depends(get_db)):
    """List all registered NWP, regional, and AI forecasting models."""
    return db.query(WeatherModel).all()

@router.get("/{model_id}", response_model=WeatherModelResponse)
def get_weather_model(model_id: str, db: Session = Depends(get_db)):
    """Get metadata and operational status for a specific model."""
    model = db.query(WeatherModel).filter(WeatherModel.id == model_id.upper()).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")
    return model

@router.get("/{model_id}/skill", response_model=List[ModelSkillResponse])
def get_model_skills(
    model_id: str,
    region_id: Optional[str] = Query(None, description="Filter by region identifier"),
    lead_hours: Optional[int] = Query(None, description="Filter by lead time (24, 48, 72)"),
    weather_regime: Optional[str] = Query(None, description="Filter by regime (e.g. HEAVY_RAINFALL)"),
    season: Optional[str] = Query(None, description="Filter by season (e.g. SW_MONSOON)"),
    db: Session = Depends(get_db)
):
    """
    Retrieve historical model skill benchmarks partitioned by
    region, lead time, season, and synoptic weather regime.
    """
    m_clean = model_id.upper()
    query = db.query(ModelSkill).filter(ModelSkill.model_id == m_clean)
    if region_id:
        query = query.filter(ModelSkill.region_id == region_id)
    if lead_hours:
        query = query.filter(ModelSkill.lead_hours == lead_hours)
    if weather_regime:
        query = query.filter(ModelSkill.weather_regime == weather_regime.upper())
    if season:
        query = query.filter(ModelSkill.season == season.upper())
        
    results = query.all()
    if not results:
        # P0-10: Cold-start explicit prior instead of returning unconstrained cross-region records
        default_mae = 9.2 if m_clean == "NCUM" else 18.5 if m_clean == "GFS" else 11.4 if m_clean == "WRF" else 11.8
        return [
            ModelSkillResponse(
                id=f"bootstrap_{m_clean.lower()}",
                model_id=m_clean,
                region_id=region_id or "GLOBAL",
                variable="rainfall",
                lead_hours=lead_hours or 48,
                season=season or "SW_MONSOON",
                weather_regime=weather_regime or "NORMAL",
                metric="MAE",
                value=default_mae,
                sample_count=0,
                evaluation_period="BOOTSTRAP_PRIOR",
                source_type="BOOTSTRAP_PRIOR",
                quality_status="UNVALIDATED"
            )
        ]
    return results

