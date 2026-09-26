from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from app.demo.scenario_generator import scenario_generator
from app.schemas.all_schemas import FusionResponse, FusionExplanationResponse

router = APIRouter(prefix="/fusion", tags=["Adaptive Forecast Fusion"])

@router.get("/current")
def get_current_fusion(
    region_id: str = Query("IN_TELANGANA_HYDERABAD", description="Target region"),
    variable: str = Query("rainfall", description="Variable: rainfall | temperature | wind_speed"),
    lead_hours: int = Query(48, description="Lead hours: 24 | 48 | 72"),
    weather_regime: str = Query("HEAVY_RAINFALL", description="Weather regime: NORMAL | HEAVY_RAINFALL | CONVECTIVE | TRANSITION_UNCERTAIN"),
    strategy: str = Query("ADAPTIVE_ML", description="Adaptive blending strategy: ADAPTIVE_ML (Supervised ML Meta-Model) | ADAPTIVE_RELIABILITY (Heuristic Baseline)")
):
    """
    Returns the dynamically blended forecast with full multi-model trust weights,
    disagreement diagnostics, event probability, and epistemic confidence.
    Supports toggling between ADAPTIVE_ML and ADAPTIVE_RELIABILITY baseline.
    """
    res = scenario_generator.execute_pipeline(
        custom_context={
            "region_id": region_id,
            "variable": variable,
            "lead_hours": lead_hours,
            "weather_regime": weather_regime,
            "strategy": strategy
        }
    )
    
    return {
        "id": f"FUSION_{region_id}_{variable}_{lead_hours}H",
        "region_id": res["region_id"],
        "variable": res["variable"],
        "lead_hours": res["lead_hours"],
        "weather_regime": res["weather_regime"],
        "valid_time": res["valid_time"],
        "fused_value": res["fused_value"],
        "simple_average_value": res["baselines"]["simple_average"],
        "static_blend_value": res["baselines"]["static_blend"],
        "probability": res["uncertainty"]["probability"],
        "confidence": res["uncertainty"]["confidence"],
        "confidence_score": res["uncertainty"]["confidence_score"],
        "disagreement": res["disagreement"]["disagreement_level"],
        "disagreement_score": res["disagreement"]["disagreement_score"],
        "uncertainty": res["uncertainty"]["uncertainty_margin"],
        "source_type": res["data_type"],
        "weights": res["weights"],
        "model_forecasts": res["model_forecasts"],
        "extreme_guidance": res["extreme_guidance"],
        "data_health": res["data_health"]
    }

@router.get("/weights")
def get_fusion_weights(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    lead_hours: int = Query(48),
    weather_regime: str = Query("HEAVY_RAINFALL"),
    strategy: str = Query("ADAPTIVE_ML", description="ADAPTIVE_ML | ADAPTIVE_RELIABILITY")
):
    """
    Returns normalized model trust weights w_i and reliability breakdown.
    Guarantees: sum(weights) == 1.0.
    """
    res = scenario_generator.execute_pipeline(
        custom_context={
            "region_id": region_id,
            "lead_hours": lead_hours,
            "weather_regime": weather_regime,
            "strategy": strategy
        }
    )
    return {
        "region_id": region_id,
        "lead_hours": lead_hours,
        "weather_regime": weather_regime,
        "weights": res["weights"],
        "sum_of_weights": round(sum(w["weight"] for w in res["weights"]), 4),
        "disagreement_score": res["disagreement"]["disagreement_score"]
    }

@router.get("/explanation")
def get_fusion_explanation(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    variable: str = Query("rainfall"),
    lead_hours: int = Query(48),
    weather_regime: str = Query("HEAVY_RAINFALL")
):
    """
    Returns 'Why this forecast?' explainable decision support factors,
    explaining dominant model allocation, bias penalties, and confidence rationale.
    """
    res = scenario_generator.execute_pipeline(
        custom_context={
            "region_id": region_id,
            "variable": variable,
            "lead_hours": lead_hours,
            "weather_regime": weather_regime
        }
    )
    return res["explanation"]

@router.get("/weight-map")
def get_spatial_model_weight_map(
    variable: str = Query("rainfall", description="Forecast variable: rainfall | temperature | wind_speed"),
    lead_hours: int = Query(48, description="Forecast lead hours: 24 | 48 | 72"),
    season: str = Query("SW_MONSOON", description="Season: SW_MONSOON | POST_MONSOON | PRE_MONSOON | WINTER"),
    weather_regime: str = Query("HEAVY_RAINFALL", description="Atmospheric regime: NORMAL | HEAVY_RAINFALL | CONVECTIVE | TRANSITION_UNCERTAIN"),
    model_focus: Optional[str] = Query(None, description="Optional target model e.g. WRF | NCUM | GFS | AI_WEATHER to focus weight distribution"),
    strategy: str = Query("ADAPTIVE_ML", description="Blending strategy: ADAPTIVE_ML (Supervised ML Meta-Model) | ADAPTIVE_RELIABILITY (Heuristic Baseline)")
):
    """
    SIH26081 Key Deliverable: Dynamic Spatial Model-Weight Map.
    Returns GeoJSON FeatureCollection of 14 Indian meteorological subdivisions with:
    - Subdivision boundary polygons (GeoJSON RFC 7946 compliant)
    - Normalized model trust weights (w_i >= 0, sum(w_i) == 1.0)
    - Dominant model per region & physical meteorological rationale
    - Dynamic responsiveness to lead time changes (24h -> 48h -> 72h)
    """
    from app.intelligence.spatial_weight_map import generate_spatial_weight_map
    return generate_spatial_weight_map(
        variable=variable,
        lead_hours=lead_hours,
        season=season,
        weather_regime=weather_regime,
        model_focus=model_focus,
        strategy=strategy
    )

