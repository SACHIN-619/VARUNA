from typing import Dict, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "SCENARIO_1_NORMAL_AGREEMENT": {
        "scenario_id": "SCENARIO_1_NORMAL_AGREEMENT",
        "title": "Synoptic Convergence (Low Disagreement)",
        "description": "All 4 models converge on a moderate monsoon rainfall event. Consensus yields High Confidence.",
        "region_id": "IN_TELANGANA_HYDERABAD",
        "variable": "rainfall",
        "lead_hours": 48,
        "season": "SW_MONSOON",
        "weather_regime": "NORMAL",
        "forecasts": {
            "NCUM": 18.5,
            "GFS": 21.0,
            "WRF": 17.2,
            "AI_WEATHER": 19.0
        },
        "historical_skills": {
            "NCUM": {"MAE": 8.5, "BIAS": -0.5},
            "GFS": {"MAE": 10.2, "BIAS": 1.2},
            "WRF": {"MAE": 9.1, "BIAS": -0.8},
            "AI_WEATHER": {"MAE": 9.8, "BIAS": 0.2}
        },
        "recent_errors": {"NCUM": 1.2, "GFS": 2.0, "WRF": 1.5, "AI_WEATHER": 1.8},
        "data_type": "synthetic_demo"
    },
    
    "SCENARIO_2_SIGNATURE_HEAVY_RAINFALL": {
        "scenario_id": "SCENARIO_2_SIGNATURE_HEAVY_RAINFALL",
        "title": "Signature Demo: Monsoon Depressional Influx",
        "description": "Hero demo scenario: High model disagreement during an active monsoon depression over Telangana.",
        "region_id": "IN_TELANGANA_HYDERABAD",
        "variable": "rainfall",
        "lead_hours": 48,
        "season": "SW_MONSOON",
        "weather_regime": "HEAVY_RAINFALL",
        "forecasts": {
            "NCUM": 82.0,
            "WRF": 47.0,
            "GFS": 103.0,
            "AI_WEATHER": 64.0
        },
        "historical_skills": {
            "NCUM": {"MAE": 12.1, "BIAS": 1.0},
            "WRF": {"MAE": 13.5, "BIAS": -2.1},
            "GFS": {"MAE": 22.4, "BIAS": 14.2},
            "AI_WEATHER": {"MAE": 18.0, "BIAS": -4.5}
        },
        "recent_errors": {"NCUM": 3.4, "WRF": 4.1, "GFS": 12.5, "AI_WEATHER": 6.0},
        "data_type": "synthetic_demo"
    },

    "SCENARIO_3_HIGH_DISAGREEMENT": {
        "scenario_id": "SCENARIO_3_HIGH_DISAGREEMENT",
        "title": "Extreme Disagreement & Epistemic Uncertainty",
        "description": "Models exhibit severe bifurcation (5 mm to 110 mm). Disagreement triggers low confidence rating.",
        "region_id": "IN_TELANGANA_WARANGAL",
        "variable": "rainfall",
        "lead_hours": 72,
        "season": "SW_MONSOON",
        "weather_regime": "TRANSITION_UNCERTAIN",
        "forecasts": {
            "NCUM": 24.0,
            "GFS": 110.0,
            "WRF": 5.0,
            "AI_WEATHER": 85.0
        },
        "historical_skills": {
            "NCUM": {"MAE": 18.0, "BIAS": 2.0},
            "GFS": {"MAE": 28.0, "BIAS": 16.0},
            "WRF": {"MAE": 22.0, "BIAS": -5.0},
            "AI_WEATHER": {"MAE": 24.0, "BIAS": 6.0}
        },
        "recent_errors": {"NCUM": 8.0, "GFS": 25.0, "WRF": 12.0, "AI_WEATHER": 14.0},
        "data_type": "synthetic_demo"
    },

    "SCENARIO_4_WET_BIAS_DRIFT": {
        "scenario_id": "SCENARIO_4_WET_BIAS_DRIFT",
        "title": "Model Degradation & Dynamic Down-weighting",
        "description": "GFS develops a runaway operational wet bias. Adaptive trust engine penalizes GFS weight.",
        "region_id": "IN_TELANGANA_HYDERABAD",
        "variable": "rainfall",
        "lead_hours": 48,
        "season": "SW_MONSOON",
        "weather_regime": "HEAVY_RAINFALL",
        "forecasts": {
            "NCUM": 75.0,
            "WRF": 68.0,
            "GFS": 135.0,
            "AI_WEATHER": 62.0
        },
        "historical_skills": {
            "NCUM": {"MAE": 11.5, "BIAS": 0.5},
            "WRF": {"MAE": 12.8, "BIAS": -1.2},
            "GFS": {"MAE": 31.0, "BIAS": 28.5},
            "AI_WEATHER": {"MAE": 16.0, "BIAS": -3.0}
        },
        "recent_errors": {"NCUM": 2.8, "WRF": 3.5, "GFS": 34.0, "AI_WEATHER": 5.2},
        "data_type": "synthetic_demo"
    },

    "SCENARIO_5_MISSING_MODEL": {
        "scenario_id": "SCENARIO_5_MISSING_MODEL",
        "title": "Feed Disruption (NCUM Source Missing)",
        "description": "NCUM primary feed suffers network latency. System gracefully excludes NCUM and rebalances weights.",
        "region_id": "IN_TELANGANA_HYDERABAD",
        "variable": "rainfall",
        "lead_hours": 48,
        "season": "SW_MONSOON",
        "weather_regime": "HEAVY_RAINFALL",
        "forecasts": {
            "NCUM": None,  # Disabled / Missing
            "WRF": 55.0,
            "GFS": 92.0,
            "AI_WEATHER": 68.0
        },
        "historical_skills": {
            "NCUM": {"MAE": 12.0, "BIAS": 1.0},
            "WRF": {"MAE": 13.5, "BIAS": -2.0},
            "GFS": {"MAE": 22.0, "BIAS": 12.0},
            "AI_WEATHER": {"MAE": 17.5, "BIAS": -4.0}
        },
        "recent_errors": {"NCUM": 0.0, "WRF": 4.0, "GFS": 10.0, "AI_WEATHER": 5.5},
        "data_type": "synthetic_demo"
    },

    "SCENARIO_6_CYCLE_REVISION": {
        "scenario_id": "SCENARIO_6_CYCLE_REVISION",
        "title": "Cycle Revision & Intensification",
        "description": "Previous 00Z cycle vs Current 12Z cycle. Demonstrates What Changed diagnostics.",
        "region_id": "IN_TELANGANA_HYDERABAD",
        "variable": "rainfall",
        "lead_hours": 48,
        "season": "SW_MONSOON",
        "weather_regime": "HEAVY_RAINFALL",
        "forecasts": {
            "NCUM": 85.0,
            "WRF": 74.0,
            "GFS": 98.0,
            "AI_WEATHER": 71.0
        },
        "previous_cycle": {
            "fused_value": 42.0,
            "probability": 35.0,
            "confidence": "HIGH",
            "disagreement": "LOW",
            "model_forecasts": {"NCUM": 40.0, "WRF": 38.0, "GFS": 48.0, "AI_WEATHER": 41.0}
        },
        "historical_skills": {
            "NCUM": {"MAE": 11.0, "BIAS": 0.8},
            "WRF": {"MAE": 12.5, "BIAS": -1.5},
            "GFS": {"MAE": 20.0, "BIAS": 10.0},
            "AI_WEATHER": {"MAE": 16.0, "BIAS": -3.5}
        },
        "recent_errors": {"NCUM": 3.0, "WRF": 3.5, "GFS": 8.0, "AI_WEATHER": 4.5},
        "data_type": "synthetic_demo"
    },

    "SCENARIO_7_EXTREME_EVENT_ALERT": {
        "scenario_id": "SCENARIO_7_EXTREME_EVENT_ALERT",
        "title": "Red Alert Very Heavy Inundation",
        "description": "Precipitation exceeds 150 mm triggering Red Warning decision support.",
        "region_id": "IN_TELANGANA_ADILABAD",
        "variable": "rainfall",
        "lead_hours": 24,
        "season": "SW_MONSOON",
        "weather_regime": "HEAVY_RAINFALL",
        "forecasts": {
            "NCUM": 165.0,
            "WRF": 182.0,
            "GFS": 145.0,
            "AI_WEATHER": 155.0
        },
        "historical_skills": {
            "NCUM": {"MAE": 14.0, "BIAS": 2.0},
            "WRF": {"MAE": 13.0, "BIAS": 1.0},
            "GFS": {"MAE": 25.0, "BIAS": 15.0},
            "AI_WEATHER": {"MAE": 19.0, "BIAS": -5.0}
        },
        "recent_errors": {"NCUM": 4.0, "WRF": 3.0, "GFS": 12.0, "AI_WEATHER": 6.0},
        "data_type": "synthetic_demo"
    }
}
