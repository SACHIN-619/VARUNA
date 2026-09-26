from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.providers import PROVIDERS
from app.demo.scenario_generator import scenario_generator

router = APIRouter(prefix="/forecasts", tags=["Forecast Ingestion & Retrieval"])

@router.get("")
def get_raw_forecasts(
    region_id: str = Query("IN_TELANGANA_HYDERABAD", description="Target region ID"),
    variable: str = Query("rainfall", description="Variable: rainfall | temperature | wind_speed"),
    lead_hours: int = Query(48, description="Lead hours: 24 | 48 | 72")
):
    """
    Retrieves current multi-model forecast feeds across NCUM, GFS, WRF, and AI models.
    """
    res = scenario_generator.execute_pipeline(
        custom_context={"region_id": region_id, "variable": variable, "lead_hours": lead_hours}
    )
    
    forecast_items = []
    valid_time = datetime.now(timezone.utc) + timedelta(hours=lead_hours)
    
    for m_id, val in res["model_forecasts"].items():
        forecast_items.append({
            "model_id": m_id,
            "region_id": region_id,
            "variable": variable,
            "lead_hours": lead_hours,
            "valid_time": valid_time.isoformat(),
            "value": val,
            "unit": "mm" if variable == "rainfall" else "C" if variable == "temperature" else "km/h",
            "quality_flag": "PASSED" if val is not None else "UNAVAILABLE",
            "provenance": res["data_type"]
        })
        
    return {
        "region_id": region_id,
        "variable": variable,
        "lead_hours": lead_hours,
        "valid_time": valid_time.isoformat(),
        "source_type": res["data_type"],
        "forecasts": forecast_items
    }

@router.get("/{forecast_id}")
def get_forecast_by_id(forecast_id: str):
    """Retrieves forecast cycle provenance and values by forecast cycle ID."""
    return {
        "forecast_id": forecast_id,
        "model_id": "NCUM",
        "cycle_time": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETED",
        "source_type": "synthetic_demo",
        "values_count": 4
    }
