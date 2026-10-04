"""
VARUNA Canonical Meteorological Data Contract.
SIH 2026 Problem Statement: SIH26081

Establishes a single, canonical, immutable schema across all heterogeneous
numerical weather prediction (NWP), regional, and machine learning forecast sources.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict

class MeteorologicalVariable(str, Enum):
    RAINFALL = "rainfall"
    TEMPERATURE = "temperature"
    WIND_SPEED = "wind_speed"
    # Extensible variables
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    SOLAR_RADIATION = "solar_radiation"


class DataProvenance(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    PUBLIC_BENCHMARK = "PUBLIC_BENCHMARK"
    SYNTHETIC_STRESS_TEST = "SYNTHETIC_STRESS_TEST"
    AUTHORIZED_OPERATIONAL_FEED = "AUTHORIZED_OPERATIONAL_FEED"



class QualityFlag(str, Enum):
    PASSED = "PASSED"
    SUSPECT = "SUSPECT"
    INTERPOLATED = "INTERPOLATED"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"


class CanonicalWeatherRecord(BaseModel):
    """
    Single Canonical Record for all weather data inside VARUNA.
    Heterogeneous sources are normalized into this contract at ingestion.
    """
    forecast_time: datetime = Field(..., description="Timestamp when the forecast was generated (UTC)")
    issue_time: datetime = Field(..., description="Timestamp when the model run was initialized/issued (UTC)")
    valid_time: datetime = Field(..., description="Target forecast validity timestamp (UTC)")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    region_id: str = Field(..., description="Standardized regional identifier e.g. IN_TELANGANA_HYDERABAD")
    variable: str = Field(..., description="Meteorological variable (rainfall | temperature | wind_speed)")
    lead_time: int = Field(..., ge=0, description="Forecast lead time in hours (e.g. 24, 48, 72)")
    value: float = Field(..., description="Normalized numerical value in canonical units")
    unit: str = Field(..., description="Canonical unit: mm (rainfall), °C (temperature), m/s (wind_speed)")
    model_id: str = Field(..., description="Forecasting model identifier: NCUM | GFS | WRF | AI_WEATHER")
    model_version: str = Field("v1.0", description="Model version or release tag")
    source: str = Field(..., description="Originating organization or archive e.g. NCMRWF, NOAA, IMD")
    resolution: str = Field(..., description="Spatial grid resolution e.g. 12km, 25km, 3km, 0.25deg")
    ensemble_member: Optional[str] = Field(None, description="Ensemble member ID if applicable e.g. 'ens_01'")
    quality_flag: str = Field(QualityFlag.PASSED.value, description="Data quality status flag")
    provenance: str = Field(DataProvenance.SYNTHETIC_STRESS_TEST.value, description="Data provenance badge")
    ingestion_id: str = Field(..., description="Unique ingestion batch identifier")
    dataset_id: str = Field(..., description="Registered dataset identifier")

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator("variable")
    @classmethod
    def validate_variable(cls, v: str) -> str:
        clean = v.strip().lower()
        mapping = {
            "rain": "rainfall",
            "rainfall": "rainfall",
            "precip": "rainfall",
            "precipitation": "rainfall",
            "temp": "temperature",
            "temperature": "temperature",
            "t2m": "temperature",
            "wind": "wind_speed",
            "wind_speed": "wind_speed",
            "ws": "wind_speed",
            "humidity": "humidity",
            "relative_humidity": "humidity",
            "rel_hum": "humidity",
            "rh": "humidity",
            "pressure": "pressure",
            "mslp": "pressure",
            "solar_radiation": "solar_radiation",
            "radiation": "solar_radiation"
        }
        if clean not in mapping:
            raise ValueError(f"Unsupported meteorological variable '{v}'. Supported: {list(mapping.keys())}")
        return mapping[clean]

    @field_validator("unit")
    @classmethod
    def validate_canonical_units(cls, u: str, info) -> str:
        # Canonical target units:
        # rainfall -> mm
        # temperature -> °C
        # wind_speed -> m/s
        # humidity -> %
        # pressure -> hPa
        # solar_radiation -> W/m2
        return u.strip()


class CanonicalBatchIngestionRequest(BaseModel):
    dataset_id: str
    provenance: str = DataProvenance.PUBLIC_BENCHMARK.value
    records: List[CanonicalWeatherRecord]
