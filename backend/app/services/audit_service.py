"""Append-only, hash-chained audit trail writer + integrity verifier."""
import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.audit import AuditLog

logger = logging.getLogger("varuna-audit")
_lock = threading.Lock()


def _digest(row: Dict[str, Any], prev_hash: str) -> str:
    payload = json.dumps(row, sort_keys=True, default=str) + "|" + (prev_hash or "GENESIS")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical(entry: AuditLog) -> Dict[str, Any]:
    ts = entry.timestamp
    if ts is not None and ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return {
        "id": entry.id, "seq": entry.seq, "actor": entry.actor, "actor_role": entry.actor_role,
        "action": entry.action, "entity_type": entry.entity_type, "entity_id": entry.entity_id,
        "result": entry.result, "reason": entry.reason, "request_ip": entry.request_ip,
        "metadata": entry.audit_metadata, "timestamp": ts.isoformat() if ts else None,
    }


def record(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    actor: Any = None,
    result: str = "SUCCESS",
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request_ip: Optional[str] = None,
    commit: bool = True,
) -> Optional[AuditLog]:
    """Append one audit event. Never raises into the caller (audit failure is logged)."""
    try:
        with _lock:
            last = db.query(AuditLog).filter(AuditLog.seq.isnot(None)).order_by(AuditLog.seq.desc()).first()
            seq = (last.seq + 1) if last else 1
            prev_hash = last.hash if last else "GENESIS"
            entry = AuditLog(
                seq=seq,
                actor=str(getattr(actor, "email", None) or (actor if isinstance(actor, str) else "SYSTEM"))[:100],
                actor_role=getattr(actor, "role", None),
                action=str(action)[:100], entity_type=str(entity_type)[:50],
                entity_id=str(entity_id)[:120] if entity_id is not None else None,
                result=result, reason=str(reason)[:500] if reason is not None else None,
                request_ip=str(request_ip)[:64] if request_ip else None,
                audit_metadata=metadata or {},
                # naive UTC: identical on SQLite and PostgreSQL "timestamp without time zone",
                # whatever the server session TimeZone is (keeps the hash chain stable on Neon)
                timestamp=datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None),
                prev_hash=prev_hash,
            )
            # id must exist before hashing
            import uuid
            entry.id = str(uuid.uuid4())
            entry.hash = _digest(_canonical(entry), prev_hash)
            db.add(entry)
            if commit:
                db.commit()
            return entry
    except Exception as e:  # pragma: no cover
        logger.error(f"Audit write failed for {action}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None


def verify_chain(db: Session, limit: int = 100000) -> Dict[str, Any]:
    rows = db.query(AuditLog).filter(AuditLog.seq.isnot(None)).order_by(AuditLog.seq.asc()).limit(limit).all()
    prev = "GENESIS"
    for r in rows:
        if r.prev_hash != prev:
            return {"intact": False, "checked": r.seq, "broken_at_seq": r.seq, "reason": "prev_hash mismatch (row removed or reordered)"}
        expect = _digest(_canonical(r), prev)
        if expect != r.hash:
            return {"intact": False, "checked": r.seq, "broken_at_seq": r.seq, "reason": "content hash mismatch (row edited)"}
        prev = r.hash
    return {"intact": True, "checked": len(rows), "head_hash": prev}
