"""Forecast snapshots and change notifications (traceable, with the maths that triggered them)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Integer, JSON, Boolean
from app.core.database import Base


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"

    id = Column(String(50), primary_key=True, default=lambda: f"SNAP_{uuid.uuid4().hex[:12]}")
    run_id = Column(String(80), nullable=True)
    region_id = Column(String(80), nullable=False, index=True)
    variable = Column(String(50), nullable=False)
    lead_hours = Column(Integer, nullable=False)
    source_mode = Column(String(40), nullable=False, default="DEMO")   # DEMO | DATABASE | LIVE_PUBLIC
    strategy = Column(String(40), nullable=True)
    input_hash = Column(String(64), nullable=False, index=True)
    fused_value = Column(Float, nullable=True)
    probability = Column(Float, nullable=True)
    confidence = Column(String(20), nullable=True)
    alert_level = Column(String(20), nullable=True)
    weights_json = Column(JSON, nullable=True)
    forecasts_json = Column(JSON, nullable=True)
    sources_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(50), primary_key=True, default=lambda: f"NTF_{uuid.uuid4().hex[:12]}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    severity = Column(String(20), nullable=False, default="INFO")       # INFO | WARNING | CRITICAL
    category = Column(String(40), nullable=False, default="FORECAST_CHANGE")
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=False)
    region_id = Column(String(80), nullable=True)
    variable = Column(String(50), nullable=True)
    lead_hours = Column(Integer, nullable=True)
    previous_snapshot_id = Column(String(50), nullable=True)
    current_snapshot_id = Column(String(50), nullable=True)
    math_json = Column(JSON, nullable=True)      # each rule: formula, values, threshold, triggered
    sources_json = Column(JSON, nullable=True)   # model forecasts with provenance + timestamps
    read_by = Column(JSON, nullable=True)        # list of user ids that read it
    is_read = Column(Boolean, default=False)
