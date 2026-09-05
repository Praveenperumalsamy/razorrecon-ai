"""
Shared rate limiter instance. Imported by both main.py (to register the
exception handler/middleware) and individual routers (to decorate specific
endpoints, e.g. stricter limits on /auth/login to slow brute-force attempts).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])
