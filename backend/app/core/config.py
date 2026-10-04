"""
VARUNA Application Configuration & Environment Settings.
SIH 2026 Problem Statement: SIH26081
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "VARUNA — Adaptive Forecast Intelligence Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Environment & Deployment
    APP_ENV: str = Field(default_factory=lambda: os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")))
    ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")))
    SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "sih26081_super_secret_dev_key_change_in_production_38472910"))
    LOG_LEVEL: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    AIR_GAPPED_MODE: bool = Field(default_factory=lambda: os.getenv("AIR_GAPPED_MODE", "false").lower() in ["true", "1", "yes"])

    # Database
    # Default to sqlite:///./varuna_dev.db for zero-config local runs,
    # or PostgreSQL / Neon when DATABASE_URL is supplied.
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "sqlite:///./varuna_dev.db"
        )
    )

    # Ingestion & Data Handling
    DATA_CHUNK_SIZE: int = Field(default_factory=lambda: int(os.getenv("DATA_CHUNK_SIZE", "10000")))
    DATA_STORAGE_PATH: str = Field(default_factory=lambda: os.getenv("DATA_STORAGE_PATH", os.getenv("STORAGE_LOCAL_PATH", "./data/storage")))
    ML_MODEL_PATH: str = Field(default_factory=lambda: os.getenv("ML_MODEL_PATH", "./data/storage/models"))

    # External Data Providers
    ENABLE_EXTERNAL_PROVIDERS: bool = Field(default_factory=lambda: os.getenv("ENABLE_EXTERNAL_PROVIDERS", "false").lower() in ["true", "1", "yes"])

    # LLM / Grok XAI Briefing Integration (OPTIONAL)
    # Public live data (Open-Meteo, no key for non-commercial use). Disabled automatically in AIR_GAPPED_MODE.
    LIVE_DATA_ENABLED: bool = Field(default_factory=lambda: os.getenv("LIVE_DATA_ENABLED", "true").lower() in ["true", "1", "yes"])
    OPEN_METEO_FORECAST_URL: str = Field(default_factory=lambda: os.getenv("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast"))
    OPEN_METEO_PREVIOUS_RUNS_URL: str = Field(default_factory=lambda: os.getenv("OPEN_METEO_PREVIOUS_RUNS_URL", "https://previous-runs-api.open-meteo.com/v1/forecast"))
    OPEN_METEO_ARCHIVE_URL: str = Field(default_factory=lambda: os.getenv("OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive"))
    OPEN_METEO_API_KEY: str = Field(default_factory=lambda: os.getenv("OPEN_METEO_API_KEY", ""))  # commercial plan only
    LIVE_HTTP_TIMEOUT_SECONDS: float = Field(default_factory=lambda: float(os.getenv("LIVE_HTTP_TIMEOUT_SECONDS", "20")))

    # India-first sources (see app/services/india_sources.py and DATA_SOURCES.md)
    IMD_API_ENABLED: bool = Field(default_factory=lambda: os.getenv("IMD_API_ENABLED", "false").lower() in ["true", "1", "yes"])
    IMD_API_BASE_URL: str = Field(default_factory=lambda: os.getenv("IMD_API_BASE_URL", "https://api.imd.gov.in/api/v1"))
    IMD_API_KEY: str = Field(default_factory=lambda: os.getenv("IMD_API_KEY", ""))
    IMD_API_KEY_HEADER: str = Field(default_factory=lambda: os.getenv("IMD_API_KEY_HEADER", "Authorization"))
    IMD_STATION_MAP: str = Field(default_factory=lambda: os.getenv("IMD_STATION_MAP", ""))
    IMD_RAIN_DAY_OFFSET_HOURS: int = Field(default_factory=lambda: int(os.getenv("IMD_RAIN_DAY_OFFSET_HOURS", "9")))
    NCMRWF_DROP_DIR: str = Field(default_factory=lambda: os.getenv("NCMRWF_DROP_DIR", ""))

    ENABLE_GROK: bool = Field(default_factory=lambda: os.getenv("ENABLE_GROK", "false").lower() in ["true", "1", "yes"])
    GROK_API_KEY: str = Field(default_factory=lambda: os.getenv("GROK_API_KEY", os.getenv("XAI_API_KEY", "")))
    GROK_MODEL: str = Field(default_factory=lambda: os.getenv("GROK_MODEL", os.getenv("XAI_MODEL", "grok-beta")))
    XAI_API_KEY: str = Field(default_factory=lambda: os.getenv("GROK_API_KEY", os.getenv("XAI_API_KEY", "")))
    XAI_MODEL: str = Field(default_factory=lambda: os.getenv("GROK_MODEL", os.getenv("XAI_MODEL", "grok-beta")))
    # Any OpenAI-compatible chat-completions endpoint (xAI: https://api.x.ai/v1, Groq: https://api.groq.com/openai/v1)
    LLM_BASE_URL: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.x.ai/v1"))
    LLM_TIMEOUT_SECONDS: float = Field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "4.0")))

    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://*.onrender.com",
        "*"
    ]

    # Provenance Modes: PUBLIC_BENCHMARK | SYNTHETIC_STRESS_TEST | AUTHORIZED_OPERATIONAL_FEED
    DEFAULT_DATA_PROVENANCE: str = "SYNTHETIC_STRESS_TEST"

    # Extreme Weather Thresholds (IMD Standards)
    HEAVY_RAINFALL_THRESHOLD_MM: float = 64.5   # IMD Heavy Rainfall: >= 64.5 mm/24h
    VERY_HEAVY_RAINFALL_THRESHOLD_MM: float = 115.5
    EXTREMELY_HEAVY_RAINFALL_THRESHOLD_MM: float = 204.4
    HIGH_TEMP_THRESHOLD_C: float = 40.0         # IMD Heatwave standard
    HIGH_WIND_THRESHOLD_KMH: float = 50.0       # Gale/squall threshold (~14 m/s)
    HIGH_WIND_THRESHOLD_MS: float = 14.0

    # Object Storage Provider (local | s3)
    STORAGE_PROVIDER: str = Field(default_factory=lambda: os.getenv("STORAGE_PROVIDER", "local"))
    STORAGE_LOCAL_PATH: str = Field(default_factory=lambda: os.getenv("STORAGE_LOCAL_PATH", "./data/storage"))
    STORAGE_ENDPOINT: str = Field(default_factory=lambda: os.getenv("STORAGE_ENDPOINT", ""))
    STORAGE_BUCKET: str = Field(default_factory=lambda: os.getenv("STORAGE_BUCKET", "varuna-nwp-grids"))
    STORAGE_ACCESS_KEY: str = Field(default_factory=lambda: os.getenv("STORAGE_ACCESS_KEY", ""))
    STORAGE_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("STORAGE_SECRET_KEY", ""))

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()

# Groq keys start with "gsk_" (xAI Grok keys with "xai-"). If a Groq key is configured but the base URL / model
# still point at xAI, switch to Groq's OpenAI-compatible endpoint so the briefing LLM works out of the box.
if settings.GROK_API_KEY.startswith("gsk_") and "api.x.ai" in settings.LLM_BASE_URL:
    settings.LLM_BASE_URL = "https://api.groq.com/openai/v1"
    if settings.GROK_MODEL.lower().startswith("grok"):
        settings.GROK_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        settings.XAI_MODEL = settings.GROK_MODEL

# ---------------------------------------------------------------------------
# Path anchoring: relative paths used to resolve against the *current working
# directory*, so running from the repo root vs. backend/ produced two different
# SQLite files and two copies of the ML artifacts (both were found in the repo).
# Everything relative is now anchored to the backend/ directory.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _anchor(path: str) -> str:
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(BACKEND_DIR, path))


if settings.DATABASE_URL.startswith("sqlite:///") and not settings.DATABASE_URL.startswith("sqlite:////"):
    _rel = settings.DATABASE_URL[len("sqlite:///"):]
    if _rel and _rel != ":memory:":
        settings.DATABASE_URL = "sqlite:///" + _anchor(_rel).replace("\\", "/")
settings.DATA_STORAGE_PATH = _anchor(settings.DATA_STORAGE_PATH)
settings.STORAGE_LOCAL_PATH = _anchor(settings.STORAGE_LOCAL_PATH)
settings.ML_MODEL_PATH = _anchor(settings.ML_MODEL_PATH)
