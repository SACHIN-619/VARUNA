from fastapi import APIRouter, Query
from app.demo.scenario_generator import scenario_generator

router = APIRouter(prefix="/dashboard", tags=["Dashboard Summary"])

@router.get("/summary")
def get_dashboard_summary(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    variable: str = Query("rainfall"),
    lead_hours: int = Query(48),
    weather_regime: str = Query("HEAVY_RAINFALL")
):
    """
    Unified summary endpoint powering the main Meteorological Operations Intelligence Centre.
    Provides complete state for operational overview, weight maps, diagnostics, and data health.
    """
    res = scenario_generator.execute_pipeline(
        custom_context={
            "region_id": region_id,
            "variable": variable,
            "lead_hours": lead_hours,
            "weather_regime": weather_regime
        }
    )
    
    return {
        "active_cycle": "2026-09-26T00:00:00Z",
        "region_id": res["region_id"],
        "variable": res["variable"],
        "lead_hours": res["lead_hours"],
        "weather_regime": res["weather_regime"],
        "season": res["season"],
        "fused_forecast": res["fused_value"],
        "unit": "mm" if variable == "rainfall" else "C" if variable == "temperature" else "km/h",
        "baselines": res["baselines"],
        "model_forecasts": res["model_forecasts"],
        "weights": res["weights"],
        "disagreement": res["disagreement"],
        "uncertainty": res["uncertainty"],
        "extreme_guidance": res["extreme_guidance"],
        "explanation": res["explanation"],
        "what_changed": res["what_changed"],
        "data_health": res["data_health"],
        "provenance": res["data_type"]
    }
