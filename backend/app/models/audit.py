import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = Column(String(100), default="SYSTEM_FUSION_ENGINE")  # SYSTEM, FORECASTER, ADMIN
    action = Column(String(100), nullable=False)  # INGEST_FORECAST, ADAPTIVE_FUSION, INJECT_FAILURE, REWEIGHT
    entity_type = Column(String(50), nullable=False)  # WeatherModel, FusionResult, ModelSkill
    entity_id = Column(String(50), nullable=True)
    audit_metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
