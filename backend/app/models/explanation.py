import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from app.core.database import Base

class Explanation(Base):
    __tablename__ = "explanations"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    fusion_result_id = Column(String(50), ForeignKey("fusion_results.id"), nullable=False)
    explanation_type = Column(String(50), default="WHY_THIS_FORECAST")  # WHY_THIS_FORECAST, WHAT_CHANGED, RELIABILITY_DRIFT
    factors = Column(JSON, nullable=False)  # {"positive_factors": [...], "negative_factors": [...], "dominant_model": "..."}
    text = Column(String(1000), nullable=False)  # Objective synthesized explanation grounded in computed metrics
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
