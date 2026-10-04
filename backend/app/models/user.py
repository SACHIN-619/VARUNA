import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, JSON
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    # FORECASTER | OPERATIONS | ANALYST | ADMIN | AUDITOR  (see app/core/permissions.py)
    role = Column(String(50), default="FORECASTER", nullable=False)
    hashed_password = Column(String(200), nullable=True)  # PBKDF2-HMAC-SHA256
    is_active = Column(Boolean, default=True, nullable=True)
    # Region scope: null / ["*"] = all regions, otherwise a list of region ids
    region_scope = Column(JSON, nullable=True)
    organization = Column(String(120), nullable=True)
    must_change_password = Column(Boolean, default=False, nullable=True)
    created_by = Column(String(36), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
