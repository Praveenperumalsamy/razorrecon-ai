"""
Authentication endpoints: register, login, token refresh, current user.

Registration policy:
- The very first user created in an empty database becomes an `admin`
  automatically (bootstrap). Every subsequent self-registration defaults to
  `viewer` and must be promoted by an admin via /api/auth/users/{id}/role —
  this prevents privilege escalation via open self-signup in production.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models.db_models import UserDB
from app.rate_limit import limiter
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger("razorrecon.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=72, description="10-72 characters")
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    is_first_user = db.query(UserDB).count() == 0
    user = UserDB(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="admin" if is_first_user else "viewer",
        is_active=True,
    )
    db.add(user)
    db.flush()
    logger.info("user_registered", extra={"user_id": user.id, "role": user.role})
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    from datetime import datetime, timezone

    user = db.query(UserDB).filter(UserDB.email == form_data.username.lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Deliberately identical error for "no such user" and "wrong password"
        # to avoid leaking which emails are registered.
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    user.last_login_at = datetime.now(timezone.utc).isoformat()
    db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise JWTError("Not a refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(UserDB).filter(UserDB.id == data.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: UserDB = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _admin: UserDB = Depends(require_role("admin"))):
    return db.query(UserDB).all()


class RoleUpdateRequest(BaseModel):
    role: str = Field(pattern="^(admin|reviewer|viewer)$")


@router.post("/users/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: str,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    _admin: UserDB = Depends(require_role("admin")),
):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    db.flush()
    return user
