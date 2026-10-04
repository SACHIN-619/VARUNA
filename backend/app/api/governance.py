"""
Separation of duties.

  * Analysts PROPOSE scientific changes; administrators APPROVE or REJECT them; nobody approves their own proposal.
  * Administrators manage users and configuration but cannot write forecast values, skill numbers or audit rows directly.
  * Every step is written to the hash-chained audit trail.

  GET  /governance/config                 current system configuration                (config:view)
  GET  /governance/proposals              list proposals                              (change:propose | change:approve | audit:view)
  POST /governance/proposals              create a proposal                           (change:propose)
  POST /governance/proposals/{id}/approve approve + apply                             (change:approve)
  POST /governance/proposals/{id}/reject  reject with reason                          (change:approve)
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.core.permissions import has_permission
from app.models.governance import ChangeProposal, SystemConfig
from app.models.user import User
from app.services.audit_service import record as audit

router = APIRouter(prefix="/governance", tags=["Governance (separation of duties)"])

CHANGE_TYPES = {
    "SET_DEFAULT_STRATEGY": "Change the default trust strategy (payload: {strategy})",
    "RECALIBRATE_SKILL": "Fold verification history into model skill (payload: {region_id, variable, lead_hours})",
    "REFIT_STACKER": "Refit bias-corrected stackers from stored live backfill history (payload: {})",
}
STRATEGIES = {"ADAPTIVE_ML", "ADAPTIVE_RELIABILITY", "BIAS_CORRECTED_STACK"}
DEFAULT_CONFIG = {"default_strategy": "ADAPTIVE_ML"}


class ProposalIn(BaseModel):
    change_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    justification: str = Field(..., min_length=10, max_length=1000)


class ReviewIn(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


def get_config(db: Session) -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    for row in db.query(SystemConfig).all():
        cfg[row.key] = row.value
    return cfg


def _out(p: ChangeProposal) -> Dict[str, Any]:
    return {"id": p.id, "change_type": p.change_type, "description": CHANGE_TYPES.get(p.change_type),
            "payload": p.payload, "justification": p.justification, "status": p.status,
            "proposed_by": p.proposed_by_email, "reviewed_by": p.reviewed_by_email, "review_reason": p.review_reason,
            "result": p.result, "created_at": p.created_at.isoformat() if p.created_at else None,
            "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None}


@router.get("/config")
def read_config(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not any(has_permission(user.role, p) for p in ("config:view", "change:propose", "change:approve")):
        raise HTTPException(403, f"Your role ({user.role}) cannot view configuration.")
    return {"config": get_config(db), "change_types": CHANGE_TYPES}


@router.get("/proposals")
def list_proposals(status: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not any(has_permission(user.role, p) for p in ("change:propose", "change:approve", "audit:view")):
        raise HTTPException(403, f"Your role ({user.role}) cannot view change proposals.")
    q = db.query(ChangeProposal)
    if status:
        q = q.filter(ChangeProposal.status == status.upper())
    return [_out(p) for p in q.order_by(ChangeProposal.created_at.desc()).limit(200).all()]


@router.post("/proposals", status_code=201)
def create_proposal(req: ProposalIn, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("change:propose"))):
    ct = req.change_type.upper()
    if ct not in CHANGE_TYPES:
        raise HTTPException(422, f"Unknown change_type. Allowed: {sorted(CHANGE_TYPES)}")
    if ct == "SET_DEFAULT_STRATEGY" and str(req.payload.get("strategy", "")).upper() not in STRATEGIES:
        raise HTTPException(422, f"payload.strategy must be one of {sorted(STRATEGIES)}")
    p = ChangeProposal(change_type=ct, payload=req.payload, justification=req.justification,
                       proposed_by=user.id, proposed_by_email=user.email)
    db.add(p)
    db.commit()
    db.refresh(p)
    audit(db, "CHANGE_PROPOSED", "CHANGE_PROPOSAL", p.id, actor=user, reason=req.justification,
          metadata={"change_type": ct, "payload": req.payload},
          request_ip=request.client.host if request.client else None)
    return _out(p)


def _apply(db: Session, p: ChangeProposal, admin: User) -> Dict[str, Any]:
    if p.change_type == "SET_DEFAULT_STRATEGY":
        val = str(p.payload.get("strategy")).upper()
        row = db.query(SystemConfig).filter(SystemConfig.key == "default_strategy").first()
        before = row.value if row else DEFAULT_CONFIG["default_strategy"]
        if row is None:
            row = SystemConfig(key="default_strategy")
            db.add(row)
        row.value, row.updated_by, row.updated_at = val, admin.email, datetime.now(timezone.utc)
        db.commit()
        return {"default_strategy": {"before": before, "after": val}}
    if p.change_type == "RECALIBRATE_SKILL":
        from app.services.data_pipeline import data_pipeline
        pl = p.payload or {}
        return data_pipeline.update_model_skills_from_history(
            db=db, region_id=pl.get("region_id", "IN_TELANGANA_HYDERABAD"), variable=pl.get("variable", "rainfall"),
            lead_hours=int(pl.get("lead_hours", 48)), season=pl.get("season", "SW_MONSOON"),
            weather_regime=pl.get("weather_regime", "HEAVY_RAINFALL"))
    if p.change_type == "REFIT_STACKER":
        from app.services.live_sources import refit_stackers_from_db
        return {"stackers_refitted": refit_stackers_from_db(db)}
    raise ValueError("unknown change type")


@router.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: str, req: ReviewIn, request: Request, db: Session = Depends(get_db),
            admin: User = Depends(require_permission("change:approve"))):
    p = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
    if not p:
        raise HTTPException(404, "Proposal not found.")
    if p.status != "PENDING":
        raise HTTPException(409, f"Proposal is already {p.status}.")
    if p.proposed_by == admin.id:
        audit(db, "CHANGE_APPROVE", "CHANGE_PROPOSAL", p.id, actor=admin, result="DENIED", reason="self-approval")
        raise HTTPException(403, "You cannot approve your own proposal (separation of duties).")
    p.reviewed_by, p.reviewed_by_email, p.review_reason = admin.id, admin.email, req.reason
    p.reviewed_at = datetime.now(timezone.utc)
    try:
        result = _apply(db, p, admin)
        p.status, p.result = "APPLIED", result
    except Exception as exc:
        db.rollback()
        p = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
        p.reviewed_by, p.reviewed_by_email, p.review_reason = admin.id, admin.email, req.reason
        p.reviewed_at = datetime.now(timezone.utc)
        p.status, p.result = "FAILED", {"error": str(exc)[:500]}
    db.commit()
    audit(db, "CHANGE_APPROVE", "CHANGE_PROPOSAL", p.id, actor=admin, result="SUCCESS" if p.status == "APPLIED" else "FAILED",
          reason=req.reason, metadata={"change_type": p.change_type, "payload": p.payload, "result": p.result},
          request_ip=request.client.host if request.client else None)
    return _out(p)


@router.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: str, req: ReviewIn, request: Request, db: Session = Depends(get_db),
           admin: User = Depends(require_permission("change:approve"))):
    p = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
    if not p:
        raise HTTPException(404, "Proposal not found.")
    if p.status != "PENDING":
        raise HTTPException(409, f"Proposal is already {p.status}.")
    p.status, p.reviewed_by, p.reviewed_by_email, p.review_reason = "REJECTED", admin.id, admin.email, req.reason
    p.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    audit(db, "CHANGE_REJECT", "CHANGE_PROPOSAL", p.id, actor=admin, reason=req.reason,
          request_ip=request.client.host if request.client else None)
    return _out(p)
