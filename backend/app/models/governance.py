"""Separation-of-duties governance: change proposals (propose -> approve) and system configuration."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from app.core.database import Base


class ChangeProposal(Base):
    __tablename__ = "change_proposals"

    id = Column(String(50), primary_key=True, default=lambda: f"CHG_{uuid.uuid4().hex[:10]}")
    change_type = Column(String(60), nullable=False)        # SET_DEFAULT_STRATEGY | RECALIBRATE_SKILL | REFIT_STACKER
    payload = Column(JSON, nullable=True)
    justification = Column(String(1000), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING | APPROVED | REJECTED | APPLIED | FAILED
    proposed_by = Column(String(36), nullable=False)
    proposed_by_email = Column(String(100), nullable=True)
    reviewed_by = Column(String(36), nullable=True)
    reviewed_by_email = Column(String(100), nullable=True)
    review_reason = Column(String(1000), nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime, nullable=True)


class SystemConfig(Base):
    __tablename__ = "system_config"

    key = Column(String(80), primary_key=True)
    value = Column(JSON, nullable=True)
    updated_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
