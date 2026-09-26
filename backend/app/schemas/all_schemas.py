from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# --- Model Schemas ---
class WeatherModelBase(BaseModel):
    id: str
    name: str
    type: str
    provider: str
    resolution: str
    description: Optional[str] = None
    active: bool = True

class WeatherModelResponse(WeatherModelBase):
    model_metadata: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)

class ModelSkillResponse(BaseModel):
    id: str
    model_id: str
    region_id: str
    variable: str
    lead_hours: int
    season: str
    weather_regime: str
    metric: str
    value: float
    sample_count: int
    evaluation_period: str
    model_config = ConfigDict(from_attributes=True)

# --- Forecast Schemas ---
class ForecastValueItem(BaseModel):
    model_id: str
    variable: str
    lead_hours: int
    valid_time: datetime
    value: float
    unit: str
    quality_flag: str = "PASSED"

class ForecastCycleResponse(BaseModel):
    id: str
    model_id: str
    cycle_time: datetime
    initialization_time: datetime
    status: str
    source_type: str
    version: str
    model_config = ConfigDict(from_attributes=True)

# --- Fusion Schemas ---
class ModelWeightItem(BaseModel):
    model_id: str
    weight: float
    raw_forecast: Optional[float] = None
    historical_mae: Optional[float] = None
    recent_bias: Optional[float] = None
    confidence_contribution: Optional[float] = None
    status: str = "ACTIVE"  # ACTIVE, DEGRADED, EXCLUDED

class FusionResponse(BaseModel):
    id: str
    region_id: str
    variable: str
    lead_hours: int
    valid_time: datetime
    fused_value: float
    simple_average_value: float
    static_blend_value: float
    probability: float
    confidence: str
    confidence_score: float
    disagreement: str
    disagreement_score: float
    uncertainty: float
    regime: str
    source_type: str
    weights: List[ModelWeightItem]
    model_forecasts: Dict[str, float]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ExplanationFactor(BaseModel):
    positive_factors: List[str]
    negative_factors: List[str]
    dominant_model: str
    disagreement_level: str
    confidence_rationale: str
    weights_summary: Dict[str, float]

class FusionExplanationResponse(BaseModel):
    fusion_result_id: str
    explanation_type: str
    factors: ExplanationFactor
    text: str
    generated_at: datetime

# --- What Changed Schemas ---
class ForecastChangeDetail(BaseModel):
    previous_value: float
    current_value: float
    value_change: float
    previous_probability: float
    current_probability: float
    probability_change_pct_points: float
    disagreement_shift: str
    confidence_shift: str
    primary_driver: str
    model_shifts: Dict[str, float]

class WhatChangedResponse(BaseModel):
    region_id: str
    variable: str
    lead_hours: int
    previous_cycle_time: Optional[datetime] = None
    current_cycle_time: datetime
    change: ForecastChangeDetail

# --- Extreme Events Schemas ---
class ExtremeEventResponse(BaseModel):
    id: str
    region_id: str
    event_type: str
    probability: float
    severity: str
    confidence: str
    threshold: float
    valid_time: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Verification Schemas ---
class BaselineScoreItem(BaseModel):
    method: str
    model_id: Optional[str] = None
    mae: float
    rmse: float
    bias: float
    correlation: float
    pod: Optional[float] = None
    far: Optional[float] = None
    csi: Optional[float] = None
    brier: Optional[float] = None

class VerificationSummaryResponse(BaseModel):
    region_id: str
    variable: str
    lead_hours: int
    evaluation_window: str
    sample_size: int
    methods: List[BaselineScoreItem]
    adaptive_advantage_mae_reduction_pct: float
    observation_provenance: str

# --- Dashboard Schemas ---
class DashboardSummaryResponse(BaseModel):
    active_cycle: str
    region: Dict[str, Any]
    variable: str
    lead_hours: int
    weather_regime: str
    season: str
    fused_forecast: float
    baselines: Dict[str, float]
    weights: List[ModelWeightItem]
    model_forecasts: Dict[str, float]
    disagreement: Dict[str, Any]
    confidence: Dict[str, Any]
    extreme_guidance: List[ExtremeEventResponse]
    explanation: Dict[str, Any]
    data_health: Dict[str, Any]
    provenance: str

# --- Demo & Failure Injection Schemas ---
class FailureInjectionRequest(BaseModel):
    action: str = Field(..., description="simulate_model_bias | simulate_missing_model | simulate_disagreement | reset_scenario")
    model_id: Optional[str] = Field(None, description="Target model id e.g. GFS or NCUM")
    bias_magnitude: Optional[float] = Field(25.0, description="Additive bias magnitude for simulate_model_bias")

class ScenarioResponse(BaseModel):
    scenario_id: str
    title: str
    description: str
    weather_regime: str
    disagreement_level: str
    active_models: List[str]
