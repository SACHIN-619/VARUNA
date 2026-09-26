import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer
from app.core.database import Base

class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    region_id = Column(String(50), ForeignKey("regions.id"), nullable=False)
    variable = Column(String(50), nullable=False)
    lead_hours = Column(Integer, nullable=False)
    model_id = Column(String(50), ForeignKey("weather_models.id"), nullable=True)  # Null if evaluating blend method
    method = Column(String(50), nullable=False)  # INDIVIDUAL_MODEL, SIMPLE_AVERAGE, STATIC_BLEND, ADAPTIVE_BLEND
    metric = Column(String(50), nullable=False)  # MAE, RMSE, BIAS, CORR, CSI, ETS, BRIER
    forecast_value = Column(Float, nullable=True)
    observed_value = Column(Float, nullable=True)
    score = Column(Float, nullable=False)  # Computed metric value
    evaluation_window = Column(String(100), default="temporal_test_split")
    verification_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
