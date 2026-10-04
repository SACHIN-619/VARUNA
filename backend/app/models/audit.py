"""
Append-only, hash-chained audit trail.

Every row stores `prev_hash` (hash of the previous row) and `hash` = SHA-256 of its own
canonical content + prev_hash, so any edit or deletion of an earlier row breaks the chain
(`GET /api/audit/verify-chain`). ORM-level update/delete of audit rows is blocked.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Integer, event
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    seq = Column(Integer, nullable=True, index=True)
    actor = Column(String(100), default="SYSTEM")
    actor_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)          # LOGIN, LOGIN_FAILED, USER_CREATE, DATA_INGEST, ...
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(120), nullable=True)
    result = Column(String(30), nullable=True)            # SUCCESS | DENIED | FAILED
    reason = Column(String(500), nullable=True)
    request_ip = Column(String(64), nullable=True)
    audit_metadata = Column(JSON, nullable=True)
    prev_hash = Column(String(64), nullable=True)
    hash = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


@event.listens_for(AuditLog, "before_update")
def _block_update(mapper, connection, target):  # pragma: no cover - defensive
    raise PermissionError("Audit records are append-only and cannot be modified.")


@event.listens_for(AuditLog, "before_delete")
def _block_delete(mapper, connection, target):  # pragma: no cover - defensive
    raise PermissionError("Audit records are append-only and cannot be deleted.")
