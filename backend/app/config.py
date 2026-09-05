"""
Application configuration for RazorRecon AI.

All configuration is loaded from environment variables / .env file via
pydantic-settings. Secrets have NO hardcoded defaults in production mode —
the app will refuse to start rather than run with an insecure default.
"""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Environment ---
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = False
    APP_NAME: str = "RazorRecon AI"
    APP_VERSION: str = "2.0.0"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./razorrecon.db"
    USE_SQLITE: bool = True
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # --- Auth / JWT ---
    # No default in production: must be a long random value from a secrets
    # manager (see PRODUCTION.md). For local dev, .env.example provides one.
    SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_WEBHOOK: str = "300/minute"

    # --- AI Integration ---
    GEMINI_API_KEY: Optional[str] = None
    AI_REQUEST_TIMEOUT_SECONDS: int = 15

    # --- Razorpay live integration ---
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    RAZORPAY_API_BASE: str = "https://api.razorpay.com/v1"

    # --- Reconciliation thresholds ---
    AUTO_RECONCILE_THRESHOLD: float = 0.90
    AI_REVIEW_THRESHOLD: float = 0.75
    DATE_TOLERANCE_DAYS: int = 3

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"
    SENTRY_DSN: Optional[str] = None

    # --- File upload limits ---
    MAX_UPLOAD_SIZE_MB: int = 25

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _validate_cors(cls, v: str) -> str:
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        """
        Hard safety gate: refuse to boot in production with insecure defaults.
        This mirrors the app's own philosophy (precision > convenience) —
        we would rather fail fast at startup than run with a weak secret,
        wildcard CORS, or debug mode exposed to the internet.
        """
        if self.is_production:
            if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a random value >= 32 chars in production "
                    "(use `openssl rand -hex 32`). Refusing to start with an insecure key."
                )
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production.")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must not be '*' in production.")
            if self.USE_SQLITE:
                raise ValueError("SQLite is not supported in production; configure DATABASE_URL for PostgreSQL.")
        elif not self.SECRET_KEY:
            # Dev/test convenience only — never used outside local runs.
            self.SECRET_KEY = "dev-only-insecure-secret-key-do-not-use-in-production-00000"
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — read once, reused across the app."""
    return Settings()


settings = get_settings()
