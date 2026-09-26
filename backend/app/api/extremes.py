from typing import Optional, List
from fastapi import APIRouter, Query
from app.demo.scenario_generator import scenario_generator
from app.core.config import settings

router = APIRouter(prefix="/extremes", tags=["Extreme Weather Guidance"])

@router.get("")
def get_extreme_weather_guidance(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    lead_hours: int = Query(48)
):
    """
    Returns probabilistic extreme event signals for rainfall, heatwave, and squall wind.
    Non-operational decision-support guidance (does not supersede IMD official warnings).
    """
    # Rainfall
    res_rain = scenario_generator.execute_pipeline(
        custom_context={"region_id": region_id, "variable": "rainfall", "lead_hours": lead_hours}
    )
    # Temperature
    res_temp = scenario_generator.execute_pipeline(
        custom_context={"region_id": region_id, "variable": "temperature", "lead_hours": lead_hours}
    )
    # Wind Speed
    res_wind = scenario_generator.execute_pipeline(
        custom_context={"region_id": region_id, "variable": "wind_speed", "lead_hours": lead_hours}
    )

    events = [
        {
            "event_type": "HEAVY_RAINFALL",
            "variable": "rainfall",
            "threshold": settings.HEAVY_RAINFALL_THRESHOLD_MM,
            "unit": "mm",
            "fused_value": res_rain["fused_value"],
            "probability": res_rain["uncertainty"]["probability"],
            "confidence": res_rain["uncertainty"]["confidence"],
            "severity": res_rain["extreme_guidance"]["severity"],
            "status": "ACTIVE_WATCH" if res_rain["fused_value"] >= settings.HEAVY_RAINFALL_THRESHOLD_MM else "NORMAL"
        },
        {
            "event_type": "HEATWAVE",
            "variable": "temperature",
            "threshold": settings.HIGH_TEMP_THRESHOLD_C,
            "unit": "C",
            "fused_value": res_temp["fused_value"],
            "probability": res_temp["uncertainty"]["probability"],
            "confidence": res_temp["uncertainty"]["confidence"],
            "severity": "ORANGE_ALERT" if res_temp["fused_value"] >= settings.HIGH_TEMP_THRESHOLD_C else "NORMAL",
            "status": "ACTIVE_WATCH" if res_temp["fused_value"] >= settings.HIGH_TEMP_THRESHOLD_C else "NORMAL"
        },
        {
            "event_type": "HIGH_WIND_GALE",
            "variable": "wind_speed",
            "threshold": settings.HIGH_WIND_THRESHOLD_KMH,
            "unit": "km/h",
            "fused_value": res_wind["fused_value"],
            "probability": res_wind["uncertainty"]["probability"],
            "confidence": res_wind["uncertainty"]["confidence"],
            "severity": "ORANGE_ALERT" if res_wind["fused_value"] >= settings.HIGH_WIND_THRESHOLD_KMH else "NORMAL",
            "status": "ACTIVE_WATCH" if res_wind["fused_value"] >= settings.HIGH_WIND_THRESHOLD_KMH else "NORMAL"
        }
    ]

    return {
        "region_id": region_id,
        "lead_hours": lead_hours,
        "guidance_type": "DECISION_SUPPORT_NON_OFFICIAL",
        "extreme_indicators": events
    }
