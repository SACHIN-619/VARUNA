from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.region import Region
from app.demo.scenario_generator import scenario_generator

router = APIRouter(prefix="/regions", tags=["Geographic Regions"])

@router.get("")
def list_regions(db: Session = Depends(get_db)):
    """Lists registered geographical grids and administrative regions."""
    return db.query(Region).all()

@router.get("/{region_id}/forecast")
def get_region_forecast(
    region_id: str,
    variable: str = Query("rainfall", description="rainfall | temperature | wind_speed"),
    lead_hours: int = Query(48, description="24 | 48 | 72"),
    db: Session = Depends(get_db)
):
    """
    Returns localized multi-model adaptive forecast and GIS centroid coordinates.
    Demonstrates spatial weight variations across Indian terrain grids.
    """
    reg = db.query(Region).filter(Region.id == region_id).first()
    if not reg:
        # Fallback query if region not explicitly in db
        reg_info = {"id": region_id, "name": region_id, "state": "Telangana"}
    else:
        reg_info = {
            "id": reg.id,
            "name": reg.name,
            "state": reg.state,
            "centroid": reg.centroid,
            "metadata": reg.region_metadata
        }

    res = scenario_generator.execute_pipeline(
        custom_context={"region_id": region_id, "variable": variable, "lead_hours": lead_hours}
    )

    return {
        "region": reg_info,
        "variable": variable,
        "lead_hours": lead_hours,
        "fused_forecast": res["fused_value"],
        "unit": "mm" if variable == "rainfall" else "C" if variable == "temperature" else "km/h",
        "confidence": res["uncertainty"]["confidence"],
        "disagreement": res["disagreement"]["disagreement_level"],
        "weights": res["weights"],
        "extreme_guidance": res["extreme_guidance"]
    }
