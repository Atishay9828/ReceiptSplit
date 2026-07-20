from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _create_tables() -> None:
    """OCR unit tests do not need the global Testcontainers database fixture."""
    return None
