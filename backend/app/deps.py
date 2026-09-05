"""
Shared FastAPI dependencies: DB session re-export, current-user resolution,
and role-based access control guards.
"""

from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import UserDB
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ROLE_HIERARCHY = {"viewer": 0, "reviewer": 1, "admin": 2}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*allowed_roles: str):
    """
    Usage: Depends(require_role("admin", "reviewer"))
    Enforces role-based access control on top of authentication.
    """

    def _checker(user: UserDB = Depends(get_current_user)) -> UserDB:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _checker


def require_min_role(min_role: str):
    """Usage: Depends(require_min_role('reviewer')) — allows reviewer and admin."""

    def _checker(user: UserDB = Depends(get_current_user)) -> UserDB:
        if ROLE_HIERARCHY.get(user.role, -1) < ROLE_HIERARCHY.get(min_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{min_role}' or higher",
            )
        return user

    return _checker
