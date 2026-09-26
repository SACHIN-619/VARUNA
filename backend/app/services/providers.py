from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class ForecastProvider(ABC):
    """Abstract base class for all meteorological forecast sources."""

    @abstractmethod
    def get_forecast(self, region_id: str, variable: str, lead_hours: int) -> Optional[float]:
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def available_variables(self) -> List[str]:
        pass

    @abstractmethod
    def available_leads(self) -> List[int]:
        pass


class NCUMProvider(ForecastProvider):
    """National Centre for Medium Range Weather Forecasting Unified Model (NCUM) adapter."""
    
    def get_forecast(self, region_id: str, variable: str, lead_hours: int) -> Optional[float]:
        # High-skill monsoon reference
        if variable == "rainfall":
            return 82.0 if lead_hours == 48 else 75.0 if lead_hours == 24 else 60.0
        elif variable == "temperature":
            return 31.5
        elif variable == "wind_speed":
            return 28.0
        return None

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model_id": "NCUM",
            "name": "NCUM Global Unified Model",
            "type": "NWP_NATIONAL",
            "provider": "NCMRWF / MoES",
            "resolution": "12 km",
            "cycle_frequency": "00Z, 12Z",
            "provenance": "synthetic_demo"
        }

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ONLINE", "latency_ms": 18, "last_ingest": datetime.now(timezone.utc).isoformat()}

    def available_variables(self) -> List[str]:
        return ["rainfall", "temperature", "wind_speed"]

    def available_leads(self) -> List[int]:
        return [24, 48, 72]


class GFSProvider(ForecastProvider):
    """Global Forecast System (GFS) adapter (NOAA / NCEP)."""
    
    def get_forecast(self, region_id: str, variable: str, lead_hours: int) -> Optional[float]:
        if variable == "rainfall":
            return 103.0 if lead_hours == 48 else 95.0 if lead_hours == 24 else 85.0
        elif variable == "temperature":
            return 32.2
        elif variable == "wind_speed":
            return 31.0
        return None

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model_id": "GFS",
            "name": "Global Forecast System",
            "type": "NWP_GLOBAL",
            "provider": "NOAA / NCEP",
            "resolution": "25 km",
            "cycle_frequency": "00Z, 06Z, 12Z, 18Z",
            "provenance": "synthetic_demo"
        }

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ONLINE", "latency_ms": 42, "last_ingest": datetime.now(timezone.utc).isoformat()}

    def available_variables(self) -> List[str]:
        return ["rainfall", "temperature", "wind_speed"]

    def available_leads(self) -> List[int]:
        return [24, 48, 72]


class WRFProvider(ForecastProvider):
    """Weather Research and Forecasting (WRF) Regional Meso-scale Model adapter."""
    
    def get_forecast(self, region_id: str, variable: str, lead_hours: int) -> Optional[float]:
        if variable == "rainfall":
            return 47.0 if lead_hours == 48 else 52.0 if lead_hours == 24 else 38.0
        elif variable == "temperature":
            return 30.8
        elif variable == "wind_speed":
            return 25.0
        return None

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model_id": "WRF",
            "name": "WRF Regional Mesoscale",
            "type": "NWP_REGIONAL",
            "provider": "NCMRWF / IMD",
            "resolution": "3 km",
            "cycle_frequency": "00Z, 12Z",
            "provenance": "synthetic_demo"
        }

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ONLINE", "latency_ms": 25, "last_ingest": datetime.now(timezone.utc).isoformat()}

    def available_variables(self) -> List[str]:
        return ["rainfall", "temperature", "wind_speed"]

    def available_leads(self) -> List[int]:
        return [24, 48, 72]


class AIWeatherProvider(ForecastProvider):
    """Data-Driven AI Weather Model adapter."""
    
    def get_forecast(self, region_id: str, variable: str, lead_hours: int) -> Optional[float]:
        if variable == "rainfall":
            return 64.0 if lead_hours == 48 else 60.0 if lead_hours == 24 else 58.0
        elif variable == "temperature":
            return 31.0
        elif variable == "wind_speed":
            return 26.5
        return None

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model_id": "AI_WEATHER",
            "name": "AI Meteorological Meta-Model",
            "type": "AI_ML",
            "provider": "Data-Driven AI / MoES Research",
            "resolution": "0.25 deg",
            "cycle_frequency": "Continuous / 6h",
            "provenance": "synthetic_demo"
        }

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ONLINE", "latency_ms": 12, "last_ingest": datetime.now(timezone.utc).isoformat()}

    def available_variables(self) -> List[str]:
        return ["rainfall", "temperature", "wind_speed"]

    def available_leads(self) -> List[int]:
        return [24, 48, 72]

PROVIDERS = {
    "NCUM": NCUMProvider(),
    "GFS": GFSProvider(),
    "WRF": WRFProvider(),
    "AI_WEATHER": AIWeatherProvider()
}
