import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer
from app.core.database import Base

class ModelSkill(Base):
    __tablename__ = "model_skills"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(50), ForeignKey("weather_models.id"), nullable=False)
    region_id = Column(String(50), ForeignKey("regions.id"), nullable=False)
    variable = Column(String(50), nullable=False)  # rainfall, temperature, wind_speed
    lead_hours = Column(Integer, nullable=False)  # 24, 48, 72
    season = Column(String(50), nullable=False)  # SW_MONSOON, NE_MONSOON, PRE_MONSOON, POST_MONSOON, WINTER
    weather_regime = Column(String(50), nullable=False)  # NORMAL, HEAVY_RAINFALL, CONVECTIVE, TRANSITION_UNCERTAIN
    metric = Column(String(50), nullable=False)  # MAE, RMSE, BIAS, CORR, CSI, ETS, BRIER
    value = Column(Float, nullable=False)
    sample_count = Column(Integer, default=100)
    evaluation_period = Column(String(100), default="2021-2025_monsoon_benchmark")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
