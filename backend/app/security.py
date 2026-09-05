"""
Password hashing and JWT helpers for RazorRecon AI auth.

Uses the `bcrypt` library directly rather than passlib's CryptContext —
passlib 1.7.x's bcrypt backend-detection probe is incompatible with
bcrypt>=4.1 (a well-known upstream issue), so direct usage is both simpler
and more robust for production.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# bcrypt has a hard 72-byte input limit; reject longer passwords explicitly
# rather than silently truncating (silent truncation is a real-world source
# of subtle auth bugs where "password123...longtail" and "password123" hash
# identically).
_MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    pass


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > _MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(f"Password must be at most {_MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    encoded = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Raises jose.JWTError on invalid/expired token — caller converts to HTTP 401."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])



def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Raises jose.JWTError on invalid/expired token — caller converts to HTTP 401."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
