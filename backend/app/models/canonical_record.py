"""
VARUNA Canonical Weather Record ORM Model.
SIH 2026 Problem Statement: SIH26081

Stores normalized canonical observations and model forecasts with optimized composite indexes:
- (dataset_id, valid_time)
- (region_id, variable, lead_time)
- (model_id, variable, valid_time)
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Integer, Index
from app.core.database import Base

class CanonicalWeatherEntity(Base):
    __tablename__ = "canonical_weather_records"

    id = Column(String(80), primary_key=True)
    dataset_id = Column(String(100), nullable=False, index=True)
    ingestion_id = Column(String(100), nullable=False, index=True)
    forecast_time = Column(DateTime, nullable=False, index=True)
    issue_time = Column(DateTime, nullable=False)
    valid_time = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    region_id = Column(String(80), nullable=False, index=True)
    variable = Column(String(50), nullable=False, index=True)
    lead_time = Column(Integer, nullable=False, default=0)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    model_id = Column(String(50), nullable=False, index=True)
    model_version = Column(String(50), default="v1.0")
    source = Column(String(100), nullable=False)
    resolution = Column(String(50), default="12km")
    ensemble_member = Column(String(50), nullable=True)
    quality_flag = Column(String(30), default="PASSED")
    provenance = Column(String(50), default="SYNTHETIC_STRESS_TEST")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_canonical_query", "region_id", "variable", "valid_time", "lead_time"),
        Index("idx_canonical_model_perf", "model_id", "variable", "valid_time"),
        Index("idx_canonical_dataset_valid", "dataset_id", "valid_time"),
    )
