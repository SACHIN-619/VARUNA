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

    def _event(event_type, variable, res, threshold, unit):
        sig = res.get("extreme_guidance", {}) or {}
        return {
            "event_type": event_type,
            "variable": variable,
            "threshold": threshold,
            "unit": unit,
            "fused_value": res["fused_value"],
            "probability": res["uncertainty"]["probability"],
            "is_calibrated_probability": res["uncertainty"].get("is_calibrated_probability", False),
            "confidence": res["uncertainty"]["confidence"],
            "category": sig.get("category", "NORMAL"),
            "severity": sig.get("severity", "NORMAL"),
            "alert_level": sig.get("alert_level", "GREEN"),
            "status": "ACTIVE_WATCH" if sig.get("is_extreme") else "NORMAL",
        }

    events = [
        _event("HEAVY_RAINFALL", "rainfall", res_rain, settings.HEAVY_RAINFALL_THRESHOLD_MM, "mm"),
        _event("HEATWAVE", "temperature", res_temp, settings.HIGH_TEMP_THRESHOLD_C, "°C"),
        # Canonical wind unit is m/s (the previous code compared m/s values against a km/h threshold)
        _event("HIGH_WIND_GALE", "wind_speed", res_wind, settings.HIGH_WIND_THRESHOLD_MS, "m/s"),
    ]

    return {
        "region_id": region_id,
        "lead_hours": lead_hours,
        "guidance_type": "DECISION_SUPPORT_NON_OFFICIAL",
        "extreme_indicators": events
    }
