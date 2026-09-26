from typing import Dict, Any, Optional

SUPPORTED_REGIMES = ["NORMAL", "HEAVY_RAINFALL", "CONVECTIVE", "TRANSITION_UNCERTAIN"]
SUPPORTED_SEASONS = ["SW_MONSOON", "NE_MONSOON", "PRE_MONSOON", "POST_MONSOON", "WINTER"]
SUPPORTED_LEADS = [24, 48, 72]
SUPPORTED_VARIABLES = ["rainfall", "temperature", "wind_speed"]

class ContextEngine:
    """
    Synthesizes and validates spatio-temporal and synoptic context
    governing model performance dynamics.
    """
    
    @staticmethod
    def build_context(
        region_id: str,
        season: str = "SW_MONSOON",
        lead_hours: int = 48,
        variable: str = "rainfall",
        weather_regime: str = "HEAVY_RAINFALL",
        synoptic_features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        
        # Validation and normalization
        norm_regime = weather_regime.upper() if weather_regime.upper() in SUPPORTED_REGIMES else "NORMAL"
        norm_season = season.upper() if season.upper() in SUPPORTED_SEASONS else "SW_MONSOON"
        norm_lead = lead_hours if lead_hours in SUPPORTED_LEADS else 48
        norm_var = variable.lower() if variable.lower() in SUPPORTED_VARIABLES else "rainfall"
        
        context = {
            "region_id": region_id,
            "season": norm_season,
            "lead_hours": norm_lead,
            "variable": norm_var,
            "weather_regime": norm_regime,
            "synoptic_features": synoptic_features or {
                "monsoon_trough_position": "active_south_of_normal",
                "cyclonic_circulation": True,
                "low_pressure_system": "depressional_bay_of_bengal"
            }
        }
        return context
