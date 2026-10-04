"""
VARUNA Authentication, Identity & User Administration.

Endpoints:
  POST  /auth/login              OAuth2 password form -> JWT (audited, rejects inactive users)
  GET   /auth/me                 Profile + role permissions + region scope
  POST  /auth/change-password    Change own password (audited)
  GET   /auth/roles              Role -> permission matrix (for UI and documentation)
  GET   /auth/users              List users                (users:manage)
  POST  /auth/users              Create / invite a user     (users:manage, audited, no public sign-up)
  PATCH /auth/users/{id}         Change role / scope / active flag, reason required (users:manage, audited)

There is deliberately NO self-registration endpoint: accounts are created by an administrator.
"""

from typing import Optional, List
from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.core.auth import hash_password, verify_password, get_current_user, require_permission
from app.core.permissions import ROLES, PERMISSIONS, ROLE_PERMISSIONS, permissions_for
from app.models.user import User
from app.services.audit_service import record as audit

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    role: str
    permissions: List[str] = []
    region_scope: Optional[List[str]] = None
    must_change_password: bool = False
    expires_in_hours: int = 24


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: str
    is_active: bool = True
    organization: Optional[str] = None
    region_scope: Optional[List[str]] = None
    permissions: List[str] = []
    last_login_at: Optional[str] = None


class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., description="Institutional email address")
    role: str = Field("FORECASTER", description="FORECASTER | OPERATIONS | ANALYST | ADMIN | AUDITOR")
    password: Optional[str] = Field(None, min_length=8, description="Initial password; generated if omitted")
    organization: Optional[str] = None
    region_scope: Optional[List[str]] = Field(None, description='Allowed region ids, or ["*"] for all')
    reason: Optional[str] = Field(None, max_length=500)


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    region_scope: Optional[List[str]] = None
    organization: Optional[str] = None
    reason: str = Field(..., min_length=3, max_length=500, description="Why the change is made (audited)")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


def _profile(u: User) -> UserProfile:
    return UserProfile(
        id=u.id, name=u.name, email=u.email, role=u.role,
        created_at=u.created_at.isoformat() if u.created_at else "",
        is_active=u.is_active is not False,
        organization=u.organization,
        region_scope=u.region_scope,
        permissions=permissions_for(u.role),
        last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
    )


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request and request.client else None


@router.post("/login", response_model=LoginResponse)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Validates credentials and issues a signed JWT (24 h). Every attempt is audited."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or user.hashed_password is None or not verify_password(form_data.password, user.hashed_password):
        audit(db, "LOGIN_FAILED", "USER", form_data.username, actor=form_data.username, result="DENIED",
              reason="invalid credentials", request_ip=_ip(request))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.",
                            headers={"WWW-Authenticate": "Bearer"})
    if user.is_active is False:
        audit(db, "LOGIN_FAILED", "USER", user.id, actor=user, result="DENIED", reason="account deactivated",
              request_ip=_ip(request))
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is deactivated. Contact an administrator.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    audit(db, "LOGIN", "USER", user.id, actor=user, request_ip=_ip(request))
    token = create_access_token(subject=user.id, role=user.role)
    return LoginResponse(
        access_token=token, user_id=user.id, name=user.name, email=user.email, role=user.role,
        permissions=permissions_for(user.role), region_scope=user.region_scope,
        must_change_password=bool(user.must_change_password),
    )


@router.get("/me", response_model=UserProfile)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return _profile(current_user)


@router.get("/roles")
def list_roles():
    """Public description of the role/permission model (no user data)."""
    return {
        "roles": ROLES,
        "permissions": PERMISSIONS,
        "matrix": {r: sorted(p) for r, p in ROLE_PERMISSIONS.items()},
    }


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if not verify_password(req.current_password, user.hashed_password or ""):
        audit(db, "PASSWORD_CHANGE", "USER", user.id, actor=user, result="DENIED", reason="wrong current password",
              request_ip=_ip(request))
        raise HTTPException(400, "Current password is incorrect.")
    user.hashed_password = hash_password(req.new_password)
    user.must_change_password = False
    db.commit()
    audit(db, "PASSWORD_CHANGE", "USER", user.id, actor=user, request_ip=_ip(request))
    return {"status": "UPDATED"}


@router.get("/users", response_model=List[UserProfile])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_permission("users:manage"))):
    return [_profile(u) for u in db.query(User).order_by(User.created_at.asc()).all()]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(req: CreateUserRequest, request: Request, db: Session = Depends(get_db),
                admin: User = Depends(require_permission("users:manage"))):
    """Administrator-created account (no open registration). Returns a one-time initial password if generated."""
    role = req.role.upper()
    if role not in ROLES:
        raise HTTPException(422, f"Invalid role '{req.role}'. Must be one of: {ROLES}")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(409, f"A user with email '{req.email}' already exists.")
    initial = req.password or secrets.token_urlsafe(12)
    u = User(name=req.name, email=req.email, role=role, hashed_password=hash_password(initial),
             organization=req.organization, region_scope=req.region_scope or ["*"],
             must_change_password=True, created_by=admin.id, is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    audit(db, "USER_CREATE", "USER", u.id, actor=admin, reason=req.reason,
          metadata={"email": u.email, "role": role, "region_scope": u.region_scope}, request_ip=_ip(request))
    out = _profile(u).model_dump()
    if not req.password:
        out["initial_password"] = initial  # shown once; user must change it at first login
    return out


@router.patch("/users/{user_id}", response_model=UserProfile)
def update_user(user_id: str, req: UpdateUserRequest, request: Request, db: Session = Depends(get_db),
                admin: User = Depends(require_permission("users:manage"))):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found.")
    if u.id == admin.id and (req.role or req.is_active is False):
        raise HTTPException(400, "Administrators cannot change their own role or deactivate themselves.")
    before = {"role": u.role, "is_active": u.is_active is not False, "region_scope": u.region_scope,
              "organization": u.organization}
    if req.role:
        role = req.role.upper()
        if role not in ROLES:
            raise HTTPException(422, f"Invalid role. Must be one of: {ROLES}")
        u.role = role
    if req.is_active is not None:
        u.is_active = req.is_active
    if req.region_scope is not None:
        u.region_scope = req.region_scope
    if req.organization is not None:
        u.organization = req.organization
    db.commit()
    after = {"role": u.role, "is_active": u.is_active is not False, "region_scope": u.region_scope,
             "organization": u.organization}
    audit(db, "USER_UPDATE", "USER", u.id, actor=admin, reason=req.reason,
          metadata={"before": before, "after": after}, request_ip=_ip(request))
    return _profile(u)
