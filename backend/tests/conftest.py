"""
ReceiptSplit — Test Configuration

Shared fixtures, marks, and helpers for all test suites.
Import order: stdlib → third-party → app (no circular imports).
"""

from __future__ import annotations

from datetime import UTC

import pytest

# ── Test marks ────────────────────────────────────────────────────────────────
# All marks are registered in pyproject.toml [tool.pytest.ini_options].
# Use them with @pytest.mark.<name> on individual tests or test classes.

# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def fixed_clock():
    """Returns a FixedClock set to 2026-06-01T12:00:00Z."""
    from datetime import datetime

    from app.shared.clock import FixedClock
    return FixedClock(datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC))
