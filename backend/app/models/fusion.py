import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, JSON
from app.core.database import Base

class ModelWeight(Base):
    __tablename__ = "model_weights"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    fusion_result_id = Column(String(50), nullable=True, index=True)
    model_id = Column(String(50), ForeignKey("weather_models.id"), nullable=False)
    region_id = Column(String(50), ForeignKey("regions.id"), nullable=False)
    variable = Column(String(50), nullable=False)
    lead_hours = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)  # Normalized weight (0.0 to 1.0)
    confidence = Column(Float, nullable=False)
    explanation_reference = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FusionResult(Base):
    __tablename__ = "fusion_results"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    region_id = Column(String(50), ForeignKey("regions.id"), nullable=False)
    variable = Column(String(50), nullable=False)
    lead_hours = Column(Integer, nullable=False)
    valid_time = Column(DateTime, nullable=False)
    fused_value = Column(Float, nullable=False)  # Weighted blend output
    simple_average_value = Column(Float, nullable=True)  # Baseline 1
    static_blend_value = Column(Float, nullable=True)   # Baseline 2
    probability = Column(Float, nullable=False)  # Extreme event probability (0-100%)
    confidence = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    disagreement = Column(String(20), nullable=False)  # LOW, MODERATE, HIGH
    disagreement_score = Column(Float, nullable=False)  # e.g., spread/std-dev normalized
    uncertainty = Column(Float, nullable=False)  # Quantified uncertainty range (+/- mm/C)
    regime = Column(String(50), nullable=False)  # NORMAL, HEAVY_RAINFALL, CONVECTIVE, TRANSITION_UNCERTAIN
    source_type = Column(String(50), default="synthetic_demo")
    weights_json = Column(JSON, nullable=True)  # Snapshot of dynamic weights
    model_forecasts_json = Column(JSON, nullable=True)  # Snapshot of inputs {NCUM: 82, WRF: 47, ...}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
