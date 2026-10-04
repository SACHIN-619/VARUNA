"""Read-only audit trail (append-only, hash-chained). Nobody - including administrators - can edit it via the API."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.services.audit_service import verify_chain, record

router = APIRouter(prefix="/audit", tags=["Audit trail"])


@router.get("/events")
def list_events(limit: int = Query(100, le=500), offset: int = 0, action: Optional[str] = None,
                actor: Optional[str] = None, result: Optional[str] = None, db: Session = Depends(get_db),
                _u: User = Depends(require_permission("audit:view"))):
    q = db.query(AuditLog).filter(AuditLog.seq.isnot(None))
    if action:
        q = q.filter(AuditLog.action == action.upper())
    if actor:
        q = q.filter(AuditLog.actor.ilike(f"%{actor}%"))
    if result:
        q = q.filter(AuditLog.result == result.upper())
    total = q.count()
    rows = q.order_by(AuditLog.seq.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [{
        "seq": r.seq, "id": r.id, "timestamp": r.timestamp.isoformat() if r.timestamp else None, "actor": r.actor,
        "actor_role": r.actor_role, "action": r.action, "entity_type": r.entity_type, "entity_id": r.entity_id,
        "result": r.result, "reason": r.reason, "request_ip": r.request_ip, "metadata": r.audit_metadata,
        "hash": r.hash, "prev_hash": r.prev_hash} for r in rows]}


@router.get("/verify-chain")
def verify(db: Session = Depends(get_db), user: User = Depends(require_permission("audit:view"))):
    res = verify_chain(db)
    record(db, "AUDIT_CHAIN_VERIFY", "AUDIT_LOG", None, actor=user, result="SUCCESS" if res.get("intact") else "FAILED",
           metadata={k: v for k, v in res.items() if k != "head_hash"})
    return res
