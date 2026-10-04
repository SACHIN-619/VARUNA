import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.core.auth import hash_password
from app.models import (
    User, Region, WeatherModel, ModelSkill, VerificationResult,
    ForecastCycle, ForecastValue
)

from app.intelligence.spatial_weight_map import INDIAN_SUBDIVISIONS

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

# Append the 14 national meteorological subdivisions
for sub in INDIAN_SUBDIVISIONS:
    if not any(r["id"] == sub["id"] for r in REGIONS_DATA):
        REGIONS_DATA.append({
            "id": sub["id"],
            "name": sub["name"],
            "state": sub["state"],
            "country": "India",
            "centroid": sub["centroid"],
            "geometry": {"type": "Polygon", "coordinates": [sub["polygon"]]},
            "region_metadata": {
                "terrain": sub["terrain"],
                "climatic_zone": sub["climatic_zone"],
                "risk_profile": sub["risk_profile"]
            }
        })


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
    },
    # --- Publicly accessible models used by the live data path (via Open-Meteo, no API key) ---
    {
        "id": "ECMWF_IFS", "name": "ECMWF IFS HRES 0.25°", "type": "NWP_GLOBAL", "provider": "ECMWF (open data via Open-Meteo)",
        "resolution": "0.25 deg", "description": "ECMWF Integrated Forecasting System, open-data 0.25° deterministic run.",
        "active": True, "model_metadata": {"open_meteo_model": "ecmwf_ifs025", "access": "PUBLIC_API"}
    },
    {
        "id": "UKMO_UM", "name": "UK Met Office Unified Model (global 10 km)", "type": "NWP_GLOBAL",
        "provider": "UK Met Office (via Open-Meteo)", "resolution": "10 km",
        "description": "Same model family as NCMRWF's NCUM (the UM) but NOT NCUM itself.",
        "active": True, "model_metadata": {"open_meteo_model": "ukmo_global_deterministic_10km", "access": "PUBLIC_API"}
    },
    {
        "id": "ICON", "name": "DWD ICON Global", "type": "NWP_GLOBAL", "provider": "Deutscher Wetterdienst (via Open-Meteo)",
        "resolution": "13 km", "description": "DWD ICON global deterministic model.",
        "active": True, "model_metadata": {"open_meteo_model": "dwd_icon_global", "access": "PUBLIC_API"}
    },
    {
        "id": "OBS_ERA5", "name": "ERA5 reanalysis (reference)", "type": "REFERENCE", "provider": "ECMWF / Copernicus (via Open-Meteo archive)",
        "resolution": "0.25 deg", "description": "Reanalysis used as verification reference (~5 day latency). Not station observations.",
        "active": True, "model_metadata": {"access": "PUBLIC_API", "role": "VERIFICATION_REFERENCE"}
    },
    {
        "id": "OBS_IMD", "name": "IMD gridded observations (reference)", "type": "REFERENCE", "provider": "India Meteorological Department, Pune",
        "resolution": "0.25 deg rain / 1.0-0.5 deg Tmax", "description": "Gauge-based daily gridded rainfall and Tmax for India; preferred verification truth.",
        "active": True, "model_metadata": {"access": "PUBLIC_DOWNLOAD", "role": "VERIFICATION_REFERENCE"}
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
                        sample_count=0,
                        # Seeded illustrative prior - NOT verified history (treated as SEEDED_PRIOR by the pipeline)
                        evaluation_period="SEEDED_SYNTHETIC_PRIOR"
                    ))
        db.commit()

    # 4. Create role-differentiated demo users (password: varuna2026)
    DEMO_USERS = [
        {
            "name": "Meteorological Officer",
            "email": "forecaster@ncmrwf.gov.in",
            "role": "FORECASTER",
        },
        {
            "name": "Operations Officer",
            "email": "ops@ncmrwf.gov.in",
            "role": "OPERATIONS",
        },
        {
            "name": "Model Analyst",
            "email": "analyst@ncmrwf.gov.in",
            "role": "ANALYST",
        },
        {
            "name": "System Administrator",
            "email": "admin@ncmrwf.gov.in",
            "role": "ADMIN",
        },
        {
            "name": "Independent Auditor",
            "email": "auditor@ncmrwf.gov.in",
            "role": "AUDITOR",
        },
    ]
    for u_data in DEMO_USERS:
        existing = db.query(User).filter(User.email == u_data["email"]).first()
        if existing and existing.hashed_password is None:
            # Upgrade legacy demo rows (the login backdoor for hash-less users was removed)
            existing.hashed_password = hash_password("varuna2026")
        if not existing:
            db.add(User(
                name=u_data["name"],
                email=u_data["email"],
                role=u_data["role"],
                hashed_password=hash_password("varuna2026")
            ))
    db.commit()

    # 5. Seed standard Dataset Registry entries
    from app.services.dataset_registry import dataset_registry_service
    dataset_registry_service.seed_initial_datasets(db)

def _migrate_add_hashed_password(engine_to_use):
    """
    Safe DDL migration: adds hashed_password column to existing users table.
    Runs as a no-op if the column already exists.
    """
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import OperationalError, ProgrammingError
    inspector = inspect(engine_to_use)
    tables = inspector.get_table_names()
    if "users" not in tables:
        return  # Table will be created fresh by create_all
    existing_cols = [c["name"] for c in inspector.get_columns("users")]
    if "hashed_password" in existing_cols:
        return  # Column already exists
    try:
        with engine_to_use.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(200)"))
            conn.commit()
    except (OperationalError, ProgrammingError):
        pass  # Already added or unsupported syntax — ignore


# Columns added after the first release: (table, column, DDL type). Applied idempotently.
_COLUMN_MIGRATIONS = [
    ("users", "is_active", "BOOLEAN"),
    ("users", "region_scope", "JSON"),
    ("users", "organization", "VARCHAR(120)"),
    ("users", "must_change_password", "BOOLEAN"),
    ("users", "created_by", "VARCHAR(36)"),
    ("users", "last_login_at", "TIMESTAMP"),
    ("audit_logs", "seq", "INTEGER"),
    ("audit_logs", "actor_role", "VARCHAR(50)"),
    ("audit_logs", "result", "VARCHAR(30)"),
    ("audit_logs", "reason", "VARCHAR(500)"),
    ("audit_logs", "request_ip", "VARCHAR(64)"),
    ("audit_logs", "prev_hash", "VARCHAR(64)"),
    ("audit_logs", "hash", "VARCHAR(64)"),
]


def _migrate_columns(engine_to_use):
    from sqlalchemy import inspect, text
    insp = inspect(engine_to_use)
    tables = set(insp.get_table_names())
    for table, col, ddl in _COLUMN_MIGRATIONS:
        if table not in tables:
            continue
        if col in [c["name"] for c in insp.get_columns(table)]:
            continue
        if ddl == "JSON" and engine_to_use.dialect.name == "postgresql":
            ddl = "JSONB"
        try:
            with engine_to_use.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
                conn.commit()
        except Exception:
            pass


# Columns whose length grew after a database was first created (create_all never alters existing columns)
_COLUMN_WIDENINGS = [
    ("audit_logs", "entity_id", 120),
]


def _widen_columns(engine_to_use):
    if engine_to_use.dialect.name != "postgresql":
        return  # SQLite does not enforce VARCHAR lengths
    from sqlalchemy import inspect, text
    insp = inspect(engine_to_use)
    tables = set(insp.get_table_names())
    for table, col, length in _COLUMN_WIDENINGS:
        if table not in tables:
            continue
        cur = next((c for c in insp.get_columns(table) if c["name"] == col), None)
        if cur is None or getattr(cur["type"], "length", None) in (None,) or cur["type"].length >= length:
            continue
        try:
            with engine_to_use.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE VARCHAR({length})"))
                conn.commit()
        except Exception:
            pass


def init_db():
    _migrate_add_hashed_password(engine)
    _migrate_columns(engine)
    _widen_columns(engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Database schema created and seeded successfully.")
