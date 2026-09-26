import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class ForecastCycle(Base):
    __tablename__ = "forecast_cycles"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(50), ForeignKey("weather_models.id"), nullable=False)
    cycle_time = Column(DateTime, nullable=False)  # e.g., 2026-09-26 00:00:00 UTC
    initialization_time = Column(DateTime, nullable=False)
    status = Column(String(50), default="COMPLETED")  # COMPLETED, INGESTING, FAILED
    source_type = Column(String(50), default="synthetic_demo")  # synthetic_demo, historical_public, authorized_operational
    version = Column(String(20), default="v1.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    values = relationship("ForecastValue", back_populates="cycle", cascade="all, delete-orphan")


class ForecastValue(Base):
    __tablename__ = "forecast_values"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    forecast_cycle_id = Column(String(50), ForeignKey("forecast_cycles.id"), nullable=False)
    region_id = Column(String(50), ForeignKey("regions.id"), nullable=False)
    variable = Column(String(50), nullable=False)  # rainfall, temperature, wind_speed
    lead_hours = Column(Integer, nullable=False)  # 24, 48, 72
    valid_time = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # mm, C, km/h
    quality_flag = Column(String(20), default="PASSED")  # PASSED, SUSPECT, INTERPOLATED

    cycle = relationship("ForecastCycle", back_populates="values")
