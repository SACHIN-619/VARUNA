import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float
from app.core.database import Base

class ExtremeEvent(Base):
    __tablename__ = "extreme_events"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    region_id = Column(String(50), ForeignKey("regions.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # HEAVY_RAINFALL, HEATWAVE, HIGH_WIND, FLASH_FLOOD_RISK
    probability = Column(Float, nullable=False)  # e.g., 78.5%
    severity = Column(String(20), nullable=False)  # YELLOW_WATCH, ORANGE_ALERT, RED_WARNING
    confidence = Column(String(20), nullable=False)  # LOW, MODERATE, HIGH
    threshold = Column(Float, nullable=False)  # e.g., 64.5 mm
    valid_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
