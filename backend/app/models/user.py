import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    role = Column(String(50), default="FORECASTER", nullable=False)  # FORECASTER, OPERATIONS, ANALYST, ADMIN, AUDITOR
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
