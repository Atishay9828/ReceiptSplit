from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import Settings

if TYPE_CHECKING:
    import pytest


def test_cors_origins_accept_comma_separated_env_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "RECEIPTSPLIT_CORS_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000",
    )

    settings = Settings()

    assert settings.cors_origins == [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]


def test_database_url_accepts_standard_hosted_postgres_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "RECEIPTSPLIT_DATABASE_URL",
        "postgresql://user:password@db.example.com:5432/receiptsplit",
    )

    settings = Settings()

    assert settings.database_url == (
        "postgresql+asyncpg://user:password@db.example.com:5432/receiptsplit"
    )
    assert settings.database_url_sync == (
        "postgresql+psycopg2://user:password@db.example.com:5432/receiptsplit"
    )


def test_database_url_sync_translates_asyncpg_ssl_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "RECEIPTSPLIT_DATABASE_URL",
        "postgresql+asyncpg://user:password@db.example.com:5432/receiptsplit"
        "?ssl=require&application_name=receiptsplit",
    )

    settings = Settings()

    assert settings.database_url == (
        "postgresql+asyncpg://user:password@db.example.com:5432/receiptsplit"
        "?ssl=require&application_name=receiptsplit"
    )
    assert settings.database_url_sync == (
        "postgresql+psycopg2://user:password@db.example.com:5432/receiptsplit"
        "?sslmode=require&application_name=receiptsplit"
    )


def test_ocr_raw_text_storage_is_opt_in_by_default() -> None:
    settings = Settings()

    assert settings.ocr_store_raw_text is False
    assert settings.tesseract_language is None
    assert settings.tesseract_psm == 6
