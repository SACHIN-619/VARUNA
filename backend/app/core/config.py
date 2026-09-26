import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SIH26081 Hybrid AI-NWP Multi-Model Forecast Blending System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sih26081_super_secret_dev_key_change_in_production_38472910")
    
    # Database
    # Default to sqlite:///./varuna_dev.db for seamless zero-config local runs,
    # or use PostgreSQL/PostGIS in production when DATABASE_URL is supplied.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./varuna_dev.db"
    )
    
    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://*.onrender.com",
        "*"
    ]
    
    # Provenance Modes: synthetic_demo | historical_public | authorized_operational
    DEFAULT_DATA_PROVENANCE: str = "synthetic_demo"
    
    # Extreme Weather Thresholds (Configurable Decision Guidance)
    HEAVY_RAINFALL_THRESHOLD_MM: float = 64.5   # IMD Heavy Rainfall standard: >= 64.5 mm/24h
    VERY_HEAVY_RAINFALL_THRESHOLD_MM: float = 115.5
    EXTREMELY_HEAVY_RAINFALL_THRESHOLD_MM: float = 204.4
    HIGH_TEMP_THRESHOLD_C: float = 40.0         # Heatwave threshold standard
    HIGH_WIND_THRESHOLD_KMH: float = 50.0       # Gale/squall threshold
    
    # LLM / XAI Briefing Integration (Grok / Local template fallback)
    XAI_API_KEY: str = os.getenv("XAI_API_KEY", "")
    XAI_MODEL: str = os.getenv("XAI_MODEL", "grok-beta")
    
    # Object Storage Provider (local | s3 | supabase)
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")
    STORAGE_LOCAL_PATH: str = os.getenv("STORAGE_LOCAL_PATH", "./data/storage")
    STORAGE_ENDPOINT: str = os.getenv("STORAGE_ENDPOINT", "")
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "varuna-nwp-grids")
    STORAGE_ACCESS_KEY: str = os.getenv("STORAGE_ACCESS_KEY", "")
    STORAGE_SECRET_KEY: str = os.getenv("STORAGE_SECRET_KEY", "")
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
