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
