"""
ReceiptSplit — Application Configuration

All settings are read from environment variables prefixed with RECEIPTSPLIT_.
Defaults are suitable for local development only; production values must be
provided explicitly via the environment or a .env file.

Usage:
    from app.config import settings
    print(settings.database_url)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration object.  All fields map 1-to-1 to environment
    variables (RECEIPTSPLIT_<FIELD_NAME_UPPERCASED>).
    """

    model_config = SettingsConfigDict(
        env_prefix="RECEIPTSPLIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Environment ──────────────────────────────────────────────────────────
    env: Literal["development", "test", "production"] = "development"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/receiptsplit"

    # The synchronous URL is required by Alembic (migrations run synchronously).
    # Derived automatically from database_url by swapping the driver.
    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    # ── Supabase ─────────────────────────────────────────────────────────────
    supabase_url: str = "https://placeholder.supabase.co"
    supabase_service_key: str = "placeholder-key"

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Allow comma-separated string from env var."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Business Rules ────────────────────────────────────────────────────────
    # These are constants that might need environment-level overrides in tests.
    max_participants_per_room: int = 20
    max_items_per_receipt: int = 100
    max_adjustments_per_type: int = 10
    room_ttl_days: int = 30

    # ── Security ─────────────────────────────────────────────────────────────
    token_byte_length: int = 32  # 256-bit entropy — do not reduce
    room_creation_rate_limit_per_hour: int = 20  # per IP, in-process limiter
    auth_oidc_provider: str = "dev"
    auth_oidc_issuer: str | None = None
    auth_oidc_audience: str | None = None
    auth_jwks_url: str | None = None

    # OCR MVP: free-first and local by default. Use "mock" in tests/dev fixtures.
    ocr_provider: Literal["mock", "tesseract"] = "tesseract"
    ocr_max_image_bytes: int = 5 * 1024 * 1024
    ocr_max_width: int = 5000
    ocr_max_height: int = 5000
    ocr_timeout_seconds: int = 30
    tesseract_cmd: str = "tesseract"
    ocr_storage_backend: Literal["local"] = "local"
    ocr_local_storage_dir: str = ".local/ocr"
    ocr_store_raw_text: bool = True

    # ── Development helpers ───────────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_test(self) -> bool:
        return self.env == "test"

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns the singleton Settings instance.

    Cached after first call.  In tests, call get_settings.cache_clear()
    before overriding environment variables.
    """
    return Settings()


# Module-level convenience alias.
settings: Settings = get_settings()
