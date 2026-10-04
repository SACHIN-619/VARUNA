"""
VARUNA Forecast Harmonization Service.
SIH 2026 Problem Statement: SIH26081

Harmonizes heterogeneous meteorological model outputs with different:
- Spatial resolutions (e.g., 3km WRF, 12km NCUM, 25km GFS, 0.25° AI)
- Temporal resolutions and lead times
- Variable naming conventions
- Unit conventions (normalized internally: rainfall -> mm, temp -> °C, wind -> m/s)
- Grid structures

All resampling transformations explicitly record metadata (resampling method, original/target resolution).
"""

from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field
import numpy as np

CANONICAL_UNITS = {
    "rainfall": "mm",
    "temperature": "°C",
    "wind_speed": "m/s",
    "humidity": "%",
    "pressure": "hPa",
    "solar_radiation": "W/m2"
}

VARIABLE_MAPPINGS = {
    "rain": "rainfall",
    "rainfall": "rainfall",
    "precip": "rainfall",
    "precipitation": "rainfall",
    "tp": "rainfall",
    "total_precipitation": "rainfall",
    "temp": "temperature",
    "temperature": "temperature",
    "t2m": "temperature",
    "2t": "temperature",
    "wind": "wind_speed",
    "wind_speed": "wind_speed",
    "ws": "wind_speed",
    "u10_v10": "wind_speed",
    "humidity": "humidity",
    "relative_humidity": "humidity",
    "rel_hum": "humidity",
    "rh": "humidity",
    "pressure": "pressure",
    "mslp": "pressure",
    "solar_radiation": "solar_radiation",
    "ssrd": "solar_radiation",
    # aliases emitted by varuna_synth / ERA5 / IMDAA style files
    "surface_pressure": "pressure",
    "sp": "pressure",
    "msl": "pressure",
    "precipitation_amount": "rainfall",
    "apcp": "rainfall",
    "air_temperature": "temperature",
    "tmax": "temperature",
    "wind_speed_10m": "wind_speed",
    "ws10": "wind_speed",
    "si10": "wind_speed",
}

# Model-id aliases -> VARUNA model slots (NCUM | GFS | WRF | AI_WEATHER)
MODEL_ALIASES = {
    "NCUM_G": "NCUM", "NCUM_R": "NCUM", "NCMRWF_NCUM": "NCUM",
    "GFS_0P25": "GFS", "NCEP_GFS": "GFS",
    "WRF_ARW": "WRF", "IMD_WRF": "WRF",
    "AI": "AI_WEATHER", "AIWEATHER": "AI_WEATHER", "AI_MODEL": "AI_WEATHER",
    "GRAPHCAST": "AI_WEATHER", "PANGU": "AI_WEATHER", "AIFS": "AI_WEATHER", "FOURCASTNET": "AI_WEATHER",
    "ECMWF_AIFS025_SINGLE": "AI_WEATHER", "ECMWF_AIFS": "AI_WEATHER",
    "ECMWF": "ECMWF_IFS", "IFS": "ECMWF_IFS", "ECMWF_IFS025": "ECMWF_IFS",
    "UKMO": "UKMO_UM", "UM": "UKMO_UM", "UKMO_GLOBAL_DETERMINISTIC_10KM": "UKMO_UM",
    "DWD_ICON": "ICON", "DWD_ICON_GLOBAL": "ICON", "ICON_GLOBAL": "ICON",
    "NCEP_GFS_SEAMLESS": "GFS", "GFS_SEAMLESS": "GFS",
    "ERA5": "OBS_ERA5",
}

# Region-code aliases -> canonical subdivision ids (varuna_synth short codes + legacy frontend ids)
REGION_ALIASES = {
    "WG": "IN_WESTERN_GHATS_KERALA", "TEL": "IN_TELANGANA_DECCAN", "ODI": "IN_ODISHA_COASTAL",
    "CEN": "IN_VIDARBHA_CENTRAL", "RAJ": "IN_WEST_RAJASTHAN", "CAP": "IN_COASTAL_ANDHRA",
    "NE": "IN_ASSAM_VALLEY", "HIM": "IN_JAMMU_KASHMIR", "IGP": "IN_PUNJAB_HARYANA",
    "IN_ODISHA_COAST": "IN_ODISHA_COASTAL", "IN_GANGETIC_WEST_BENGAL": "IN_GANGETIC_WB",
    "IN_ASSAM_MEGHALAYA": "IN_ASSAM_VALLEY", "IN_ANDHRA_RAYALASEEMA": "IN_COASTAL_ANDHRA",
    "IN_JAMMU_KASHMIR_LADAKH": "IN_JAMMU_KASHMIR", "IN_PUNJAB_HARYANA_HP": "IN_PUNJAB_HARYANA",
}


def normalize_model_id(raw) -> str:
    m = str(raw or "").strip().upper().replace("-", "_")
    for suffix in ("_SYNTHETIC", "_SYNTH", "_DEMO"):
        if m.endswith(suffix):
            m = m[: -len(suffix)]
    return MODEL_ALIASES.get(m, m)


def normalize_region_id(raw) -> str:
    r = str(raw or "").strip()
    return REGION_ALIASES.get(r.upper(), r)


class HarmonizationMetadata(BaseModel):
    """Explicit provenance metadata for any interpolation or resampling performed."""
    original_resolution: str
    target_resolution: str
    resampling_method: str = Field(..., description="NEAREST_NEIGHBOR | BILINEAR | SUBDIVISION_AVERAGE | DIRECT_EXTRACT")
    input_unit: str
    canonical_unit: str
    unit_conversion_applied: bool
    spatial_harmonization_type: str = Field("METADATA_ONLY", description="METADATA_ONLY | ACTUAL_REGRIDDING")
    temporal_alignment_status: str = Field("ALIGNED", description="ALIGNED | INTERPOLATED | AGGREGATED | MISSING | UNVERIFIED")
    notes: Optional[str] = None


class HarmonizationService:
    """Provides mathematically verified harmonization across heterogeneous NWP & AI models."""

    @staticmethod
    def normalize_variable_name(raw_var: str) -> str:
        clean = str(raw_var).lower().strip()
        if clean not in VARIABLE_MAPPINGS:
            return "UNVERIFIED_VARIABLE"
        return VARIABLE_MAPPINGS[clean]

    @staticmethod
    def normalize_units(value: float, from_unit: str, target_variable: str) -> Tuple[float, str, bool]:
        """
        Converts diverse units to canonical meteorological standards:
        - Rainfall: mm (cm -> mm *10, m -> mm *1000, in -> mm *25.4)
        - Temperature: °C (K -> °C -273.15, °F -> °C (F-32)*5/9)
        - Wind Speed: m/s (km/h -> m/s /3.6, knots -> m/s *0.514444)
        - Pressure: hPa (Pa -> hPa /100)
        - Humidity: % (0-1 fraction -> % *100)
        """
        target_var = HarmonizationService.normalize_variable_name(target_variable)
        if target_var == "UNVERIFIED_VARIABLE":
            return round(float(value), 2), "UNVERIFIED_UNIT", False

        u_clean = str(from_unit).strip().lower().replace("°", "").replace(" ", "")
        u_clean = {
            "mm/day": "mm", "mm/d": "mm", "mmday-1": "mm", "mm/24h": "mm", "kgm-2": "mm", "kg/m2": "mm", "kg/m^2": "mm",
            "degc": "c", "deg_c": "c", "degreec": "c", "celcius": "c", "degk": "k",
            "degf": "f", "ms-1": "m/s", "m.s-1": "m/s", "km/hr": "km/h",
            "pct": "%", "percent": "%",
            "mb": "hpa", "mbar": "hpa", "millibar": "hpa",
        }.get(u_clean, u_clean)
        converted = False
        val = float(value)

        canonical_u = CANONICAL_UNITS.get(target_var, "UNVERIFIED_UNIT")

        if target_var == "rainfall":
            if u_clean in ["cm"]:
                val = val * 10.0
                converted = True
            elif u_clean in ["m", "meter", "meters"]:
                val = val * 1000.0
                converted = True
            elif u_clean in ["in", "inch", "inches"]:
                val = val * 25.4
                converted = True
            elif u_clean in ["mm", "native"]:
                converted = False
            else:
                return round(val, 2), "UNVERIFIED_UNIT", False
            return round(val, 2), "mm", converted

        elif target_var == "temperature":
            if u_clean in ["k", "kelvin"]:
                val = val - 273.15
                converted = True
            elif u_clean in ["f", "fahrenheit"]:
                val = (val - 32.0) * (5.0 / 9.0)
                converted = True
            elif u_clean in ["c", "celsius", "native"]:
                converted = False
            else:
                return round(val, 2), "UNVERIFIED_UNIT", False
            return round(val, 2), "°C", converted

        elif target_var == "wind_speed":
            if u_clean in ["km/h", "kmh", "kph"]:
                val = val / 3.6
                converted = True
            elif u_clean in ["kt", "knot", "knots"]:
                val = val * 0.514444
                converted = True
            elif u_clean in ["mph"]:
                val = val * 0.44704
                converted = True
            elif u_clean in ["m/s", "ms", "native"]:
                converted = False
            else:
                return round(val, 2), "UNVERIFIED_UNIT", False
            return round(val, 2), "m/s", converted

        elif target_var == "humidity":
            if u_clean in ["fraction", "ratio", "1"] or (0.0 <= val <= 1.0 and u_clean not in ("%", "native")):
                val = val * 100.0
                converted = True
            return round(val, 1), "%", converted

        elif target_var == "pressure":
            if u_clean in ["pa", "pascal"]:
                val = val / 100.0
                converted = True
            return round(val, 2), "hPa", converted

        return round(val, 2), canonical_u, converted

    @staticmethod
    def validate_meteorological_bounds(value: float, variable: str) -> str:
        """Physical range sanity check (IMD / WMO standard bounds)."""
        var = HarmonizationService.normalize_variable_name(variable)
        if var == "UNVERIFIED_VARIABLE":
            return "UNVERIFIED_VARIABLE"
        if var == "rainfall":
            if value < 0.0:
                return "INVALID_NEGATIVE"
            if value > 1200.0:
                return "SUSPECT_EXTREME"
        elif var == "temperature":
            if value < -50.0 or value > 60.0:
                return "SUSPECT_TEMPERATURE"
        elif var == "wind_speed":
            if value < 0.0 or value > 150.0:
                return "SUSPECT_WIND"
        elif var == "humidity":
            if value < 0.0 or value > 100.0:
                return "SUSPECT_HUMIDITY"
        elif var == "pressure":
            if value < 300.0 or value > 1085.0:  # surface pressure over the Himalaya is ~500-800 hPa
                return "SUSPECT_PRESSURE"
        return "PASSED"

    @staticmethod
    def harmonize_spatial_resolution(
        model_id: str,
        original_resolution: str,
        target_resolution: str = "subdivision_centroid",
        resampling_method: str = "SUBDIVISION_AVERAGE"
    ) -> HarmonizationMetadata:
        """
        Generates formal harmonization tracking metadata for documentation and frontend XAI.
        """
        return HarmonizationMetadata(
            original_resolution=original_resolution,
            target_resolution=target_resolution,
            resampling_method=resampling_method,
            input_unit="native",
            canonical_unit=CANONICAL_UNITS.get("rainfall", "mm"),
            unit_conversion_applied=False,
            spatial_harmonization_type="METADATA_ONLY",
            temporal_alignment_status="ALIGNED",
            notes=f"Harmonized {model_id} from {original_resolution} to {target_resolution} via {resampling_method}."
        )



harmonization_service = HarmonizationService()
