import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models import (
    User, Region, WeatherModel, ModelSkill, VerificationResult,
    ForecastCycle, ForecastValue
)

REGIONS_DATA = [
    {
        "id": "IN_TELANGANA_HYDERABAD",
        "name": "Hyderabad Urban Grid",
        "state": "Telangana",
        "country": "India",
        "centroid": {"lat": 17.3850, "lon": 78.4867},
        "geometry": {"type": "Point", "coordinates": [78.4867, 17.3850]},
        "region_metadata": {"terrain": "Deccan Plateau", "basin": "Musi River", "risk_profile": "Urban Flooding"}
    },
    {
        "id": "IN_TELANGANA_ADILABAD",
        "name": "Adilabad Northern Basin",
        "state": "Telangana",
        "country": "India",
        "centroid": {"lat": 19.6641, "lon": 78.5320},
        "geometry": {"type": "Point", "coordinates": [78.5320, 19.6641]},
        "region_metadata": {"terrain": "Forested Valley", "basin": "Godavari River", "risk_profile": "Flash Inundation"}
    },
    {
        "id": "IN_TELANGANA_WARANGAL",
        "name": "Warangal Agro-Climatic Grid",
        "state": "Telangana",
        "country": "India",
        "centroid": {"lat": 17.9689, "lon": 79.5941},
        "geometry": {"type": "Point", "coordinates": [79.5941, 17.9689]},
        "region_metadata": {"terrain": "Semi-Arid Plain", "basin": "Godavari Tributary", "risk_profile": "Agricultural Drought/Flood"}
    },
    {
        "id": "IN_KERALA_WAYANAD",
        "name": "Wayanad Western Ghats",
        "state": "Kerala",
        "country": "India",
        "centroid": {"lat": 11.6854, "lon": 76.1320},
        "geometry": {"type": "Point", "coordinates": [76.1320, 11.6854]},
        "region_metadata": {"terrain": "Orography", "basin": "Kabini River", "risk_profile": "Landslide / Cloudburst"}
    }
]

MODELS_DATA = [
    {
        "id": "NCUM",
        "name": "NCUM Global Unified Model",
        "type": "NWP_NATIONAL",
        "provider": "NCMRWF / MoES",
        "resolution": "12 km",
        "description": "Primary Indian operational NWP with specialized 4D-Var data assimilation over the monsoon trough.",
        "active": True,
        "model_metadata": {"assimilation": "4D-Var", "cycles": "00Z, 12Z", "domain": "Global"}
    },
    {
        "id": "GFS",
        "name": "Global Forecast System",
        "type": "NWP_GLOBAL",
        "provider": "NOAA / NCEP",
        "resolution": "25 km",
        "description": "Independent global numerical weather prediction baseline offering long-horizon synoptic tracking.",
        "active": True,
        "model_metadata": {"assimilation": "Hybrid 4D-EnVar", "cycles": "00Z, 06Z, 12Z, 18Z", "domain": "Global"}
    },
    {
        "id": "WRF",
        "name": "WRF Regional Mesoscale",
        "type": "NWP_REGIONAL",
        "provider": "NCMRWF / IMD",
        "resolution": "3 km",
        "description": "High-resolution regional NWP model explicitly resolving deep convective systems and local orography.",
        "active": True,
        "model_metadata": {"convection": "Explicit", "cycles": "00Z, 12Z", "domain": "Indian Subcontinent"}
    },
    {
        "id": "AI_WEATHER",
        "name": "AI Meteorological Model",
        "type": "AI_ML",
        "provider": "Data-Driven Deep Learning / MoES Research",
        "resolution": "0.25 deg",
        "description": "Graph neural network / transformer based atmospheric simulator for rapid ensemble guidance.",
        "active": True,
        "model_metadata": {"architecture": "GNN-Transformer", "cycles": "Continuous", "domain": "Global"}
    }
]

def seed_database(db: Session):
    """Populates initial reference tables if empty."""
    # 1. Models
    for m in MODELS_DATA:
        existing = db.query(WeatherModel).filter(WeatherModel.id == m["id"]).first()
        if not existing:
            db.add(WeatherModel(**m))

    # 2. Regions
    for r in REGIONS_DATA:
        existing = db.query(Region).filter(Region.id == r["id"]).first()
        if not existing:
            db.add(Region(**r))

    db.commit()

    # 3. Model Skill Records (Historical Benchmark)
    regimes = ["NORMAL", "HEAVY_RAINFALL", "CONVECTIVE", "TRANSITION_UNCERTAIN"]
    leads = [24, 48, 72]
    
    # Base skill profile: MAE values
    base_maes = {
        "NCUM": {"NORMAL": 8.0, "HEAVY_RAINFALL": 11.5, "CONVECTIVE": 14.0, "TRANSITION_UNCERTAIN": 15.0},
        "WRF": {"NORMAL": 9.2, "HEAVY_RAINFALL": 12.8, "CONVECTIVE": 12.0, "TRANSITION_UNCERTAIN": 17.5},
        "GFS": {"NORMAL": 10.5, "HEAVY_RAINFALL": 22.0, "CONVECTIVE": 21.0, "TRANSITION_UNCERTAIN": 23.0},
        "AI_WEATHER": {"NORMAL": 9.0, "HEAVY_RAINFALL": 16.5, "CONVECTIVE": 18.0, "TRANSITION_UNCERTAIN": 19.0}
    }

    if db.query(ModelSkill).count() == 0:
        for m_id, r_dict in base_maes.items():
            for regime, mae_base in r_dict.items():
                for lead in leads:
                    lead_multiplier = 1.0 + (lead - 24) * 0.015
                    db.add(ModelSkill(
                        model_id=m_id,
                        region_id="IN_TELANGANA_HYDERABAD",
                        variable="rainfall",
                        lead_hours=lead,
                        season="SW_MONSOON",
                        weather_regime=regime,
                        metric="MAE",
                        value=round(mae_base * lead_multiplier, 2),
                        sample_count=180,
                        evaluation_period="2021-2025_monsoon_benchmark"
                    ))
        db.commit()

    # 4. Create default Forecaster User
    if db.query(User).count() == 0:
        db.add(User(
            name="Meteorological Officer (MoES)",
            email="forecaster@ncmrwf.gov.in",
            role="FORECASTER"
        ))
        db.commit()

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Database schema created and seeded successfully.")
