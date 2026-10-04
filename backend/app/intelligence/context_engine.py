"""
VARUNA Canonical Context Engine.
SIH 2026 Problem Statement: SIH26081

Synthesizes multi-dimensional spatio-temporal and synoptic context
governing NWP/AI reliability dynamics into a deterministic, reproducible ContextVector.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict
import numpy as np
from app.core.config import settings

SUPPORTED_REGIMES = ["NORMAL", "HEAVY_RAINFALL", "CONVECTIVE", "TRANSITION_UNCERTAIN"]
SUPPORTED_SEASONS = ["SW_MONSOON", "NE_MONSOON", "PRE_MONSOON", "POST_MONSOON", "WINTER"]
SUPPORTED_LEADS = [24, 48, 72]
SUPPORTED_VARIABLES = ["rainfall", "temperature", "wind_speed", "humidity", "pressure"]

REGIME_INDEX_MAP = {r: i for i, r in enumerate(SUPPORTED_REGIMES)}
SEASON_INDEX_MAP = {s: i for i, s in enumerate(SUPPORTED_SEASONS)}


class ContextVector(BaseModel):
    """
    Canonical Meteorological Context Vector.
    Supplies conditioning variables to Adaptive Reliability Baseline and ML Meta-Model.
    """
    region_id: str = Field(..., description="Target geographic subdivision / station code")
    season: str = Field(..., description="Monsoon / climatological season")
    lead_time: int = Field(..., ge=0, description="Forecast lead time in hours (24, 48, 72)")
    weather_regime: str = Field(..., description="Synoptic atmospheric regime")
    variable: str = Field("rainfall", description="Forecast variable")
    historical_skill: Dict[str, float] = Field(default_factory=dict, description="Historical MAE per model")
    recent_error: Dict[str, float] = Field(default_factory=dict, description="Recent causal EMA error per model")
    model_disagreement: float = Field(0.0, ge=0.0, le=1.0, description="Multi-model spread score")
    forecast_spread: float = Field(0.0, ge=0.0, description="Standard deviation across models")
    extreme_event_flag: bool = Field(False, description="Flag indicating exceedance of hazard threshold")
    rainfall_intensity: str = Field("NORMAL", description="LIGHT | MODERATE | HEAVY | VERY_HEAVY")
    temperature_regime: str = Field("NORMAL", description="COLD | NORMAL | HEATWAVE")
    wind_regime: str = Field("CALM", description="CALM | SQUALL | GALE")
    synoptic_features: Dict[str, Any] = Field(default_factory=dict, description="Synoptic attributes")

    model_config = ConfigDict(from_attributes=True)

    def __getitem__(self, item: str) -> Any:
        # Support dict-like access: context['variable'], context['lead_hours']
        if item == "lead_hours":
            return self.lead_time
        if hasattr(self, item):
            return getattr(self, item)
        return self.synoptic_features.get(item)

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except (KeyError, AttributeError):
            return default

    def keys(self):
        return self.model_dump().keys()

    def to_numerical_vector(self, model_order: List[str] = None) -> np.ndarray:
        """
        Converts context state into a deterministic, fixed-dimension numerical vector
        suitable for direct ingestion into machine learning algorithms.
        """
        models = model_order or ["NCUM", "GFS", "WRF", "AI_WEATHER"]
        regime_idx = REGIME_INDEX_MAP.get(self.weather_regime.upper(), 0)
        season_idx = SEASON_INDEX_MAP.get(self.season.upper(), 0)

        hist_maes = [self.historical_skill.get(m, 14.0) for m in models]
        rec_errs = [self.recent_error.get(m, 0.0) for m in models]

        vector = [
            float(self.lead_time),
            float(regime_idx),
            float(season_idx),
            float(self.model_disagreement),
            float(self.forecast_spread),
            1.0 if self.extreme_event_flag else 0.0
        ] + hist_maes + rec_errs

        return np.array(vector, dtype=float)


class ContextEngine:
    """Synthesizes, validates, and standardizes atmospheric context."""

    @staticmethod
    def classify_rainfall_intensity(value_mm: float) -> str:
        """Classifies 24h rainfall according to IMD meteorological guidelines."""
        if value_mm < 2.5:
            return "NO_RAIN_VERY_LIGHT"
        elif value_mm < 15.6:
            return "LIGHT"
        elif value_mm < 64.5:
            return "MODERATE"
        elif value_mm < 115.6:
            return "HEAVY"
        elif value_mm < 204.5:
            return "VERY_HEAVY"
        else:
            return "EXTREMELY_HEAVY"

    @staticmethod
    def classify_temperature_regime(temp_c: float) -> str:
        if temp_c >= settings.HIGH_TEMP_THRESHOLD_C:
            return "HEATWAVE"
        elif temp_c < 10.0:
            return "COLDWAVE"
        return "NORMAL"

    @staticmethod
    def classify_wind_regime(wind_ms: float) -> str:
        # 14 m/s is ~50 km/h (gale threshold)
        if wind_ms >= 14.0:
            return "GALE_OR_STORM"
        elif wind_ms >= 8.5:
            return "SQUALL"
        return "CALM"

    @staticmethod
    def build_context(
        region_id: str,
        season: str = "SW_MONSOON",
        lead_hours: int = 48,
        variable: str = "rainfall",
        weather_regime: str = "HEAVY_RAINFALL",
        historical_skill: Optional[Dict[str, float]] = None,
        recent_error: Optional[Dict[str, float]] = None,
        disagreement_score: float = 0.0,
        forecast_spread: float = 0.0,
        raw_forecast_mean: Optional[float] = None,
        synoptic_features: Optional[Dict[str, Any]] = None
    ) -> ContextVector:
        """Builds a canonical ContextVector instance with physical regime detection."""
        norm_regime = weather_regime.upper() if weather_regime.upper() in SUPPORTED_REGIMES else "NORMAL"
        norm_season = season.upper() if season.upper() in SUPPORTED_SEASONS else "SW_MONSOON"
        norm_lead = lead_hours if lead_hours in SUPPORTED_LEADS else 48
        norm_var = variable.lower() if variable.lower() in SUPPORTED_VARIABLES else "rainfall"

        # Extreme threshold detection
        f_mean = raw_forecast_mean if raw_forecast_mean is not None else (75.0 if norm_regime == "HEAVY_RAINFALL" else 20.0)
        is_extreme = False
        if norm_var == "rainfall" and f_mean >= settings.HEAVY_RAINFALL_THRESHOLD_MM:
            is_extreme = True
        elif norm_var == "temperature" and f_mean >= settings.HIGH_TEMP_THRESHOLD_C:
            is_extreme = True
        elif norm_var == "wind_speed" and f_mean >= 14.0:
            is_extreme = True

        rf_intensity = ContextEngine.classify_rainfall_intensity(f_mean if norm_var == "rainfall" else 0.0)
        temp_regime = ContextEngine.classify_temperature_regime(f_mean if norm_var == "temperature" else 30.0)
        wind_regime = ContextEngine.classify_wind_regime(f_mean if norm_var == "wind_speed" else 5.0)

        default_hist = {"NCUM": 9.2, "GFS": 18.5, "WRF": 11.4, "AI_WEATHER": 11.8}
        default_recent = {"NCUM": 2.1, "GFS": 8.5, "WRF": 3.2, "AI_WEATHER": 4.0}

        return ContextVector(
            region_id=region_id,
            season=norm_season,
            lead_time=norm_lead,
            weather_regime=norm_regime,
            variable=norm_var,
            historical_skill=historical_skill or default_hist,
            recent_error=recent_error or default_recent,
            model_disagreement=round(float(disagreement_score), 3),
            forecast_spread=round(float(forecast_spread), 2),
            extreme_event_flag=is_extreme,
            rainfall_intensity=rf_intensity,
            temperature_regime=temp_regime,
            wind_regime=wind_regime,
            synoptic_features=synoptic_features or {
                "monsoon_trough_position": "active_south_of_normal",
                "low_pressure_system": "bay_of_bengal_depression"
            }
        )


context_engine = ContextEngine()
