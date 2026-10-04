"""Forecast-change notifications (bell). Each item carries the rule maths and source values with timestamps."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.core.database import get_db
from app.core.permissions import region_allowed
from app.models.notification import Notification, ForecastSnapshot
from app.models.user import User
from app.services.notification_service import to_dict

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(limit: int = 30, unread_only: bool = False, db: Session = Depends(get_db),
                       user: User = Depends(require_permission("notifications:view"))):
    rows = db.query(Notification).order_by(Notification.created_at.desc()).limit(min(limit, 200) * 3).all()
    items = [to_dict(n, user.id) for n in rows if region_allowed(user.region_scope, n.region_id)]
    unread = sum(1 for i in items if not i["read"])
    if unread_only:
        items = [i for i in items if not i["read"]]
    return {"unread": unread, "items": items[:limit]}


@router.get("/{notification_id}")
def get_notification(notification_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("notifications:view"))):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n or not region_allowed(user.region_scope, n.region_id):
        raise HTTPException(404, "Notification not found.")
    out = to_dict(n, user.id)
    snaps = {s.id: s for s in db.query(ForecastSnapshot).filter(
        ForecastSnapshot.id.in_([n.previous_snapshot_id, n.current_snapshot_id])).all()}
    out["snapshots"] = {k: {"id": s.id, "created_at": s.created_at.isoformat() if s.created_at else None,
                            "fused_value": s.fused_value, "confidence": s.confidence, "alert_level": s.alert_level,
                            "weights": s.weights_json, "forecasts": s.forecasts_json, "run_id": s.run_id,
                            "source_mode": s.source_mode, "strategy": s.strategy}
                        for k, s in (("previous", snaps.get(n.previous_snapshot_id)),
                                     ("current", snaps.get(n.current_snapshot_id))) if s is not None}
    return out


def _mark(n: Notification, user_id: str):
    ids = list(n.read_by or [])
    if user_id not in ids:
        ids.append(user_id)
        n.read_by = ids


@router.post("/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db),
              user: User = Depends(require_permission("notifications:view"))):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise HTTPException(404, "Notification not found.")
    _mark(n, user.id)
    db.commit()
    return {"status": "READ"}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(require_permission("notifications:view"))):
    count = 0
    for n in db.query(Notification).order_by(Notification.created_at.desc()).limit(500).all():
        if user.id not in (n.read_by or []):
            _mark(n, user.id)
            count += 1
    db.commit()
    return {"status": "READ", "count": count}
