from typing import Dict, Any, Optional

VARIABLE_MAPPINGS = {
    "rain": "rainfall",
    "rainfall": "rainfall",
    "precip": "rainfall",
    "precipitation": "rainfall",
    "temp": "temperature",
    "temperature": "temperature",
    "t2m": "temperature",
    "wind": "wind_speed",
    "wind_speed": "wind_speed",
    "ws": "wind_speed"
}

STANDARD_UNITS = {
    "rainfall": "mm",
    "temperature": "C",
    "wind_speed": "km/h"
}

class HarmonizationService:
    @staticmethod
    def normalize_variable_name(raw_var: str) -> str:
        clean = raw_var.lower().strip()
        return VARIABLE_MAPPINGS.get(clean, "rainfall")

    @staticmethod
    def normalize_units(value: float, from_unit: str, target_variable: str) -> float:
        """
        Converts diverse units to Indian meteorological standards:
        - Rainfall: mm
        - Temperature: Celsius (from Kelvin if > 150)
        - Wind Speed: km/h (from m/s if indicated)
        """
        target_var = HarmonizationService.normalize_variable_name(target_variable)
        if target_var == "temperature" and (from_unit.upper() in ["K", "KELVIN"] or value > 200.0):
            return round(value - 273.15, 1)
        elif target_var == "wind_speed" and from_unit.lower() in ["m/s", "mps"]:
            return round(value * 3.6, 1)
        elif target_var == "rainfall" and from_unit.lower() in ["cm"]:
            return round(value * 10.0, 1)
        return round(value, 1)

    @staticmethod
    def validate_meteorological_bounds(value: float, variable: str) -> str:
        """Physical range sanity check."""
        var = HarmonizationService.normalize_variable_name(variable)
        if var == "rainfall":
            if value < 0.0:
                return "INVALID_NEGATIVE"
            if value > 1200.0:  # World record 24h rainfall is ~1825mm
                return "SUSPECT_EXTREME"
        elif var == "temperature":
            if value < -40.0 or value > 60.0:
                return "SUSPECT_TEMPERATURE"
        elif var == "wind_speed":
            if value < 0.0 or value > 350.0:
                return "SUSPECT_WIND"
        return "PASSED"

harmonization_service = HarmonizationService()
