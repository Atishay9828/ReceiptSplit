"""
ReceiptSplit — Injectable Clock

Provides a `Clock` protocol and a concrete `SystemClock` implementation.
All code that needs the current time calls `clock.now()` rather than
`datetime.now()` directly.  This makes time-dependent logic testable
by injecting a fixed or controllable clock in tests.

Usage:
    from app.shared.clock import Clock, SystemClock

    class MyService:
        def __init__(self, clock: Clock = SystemClock()) -> None:
            self._clock = clock

        def do_thing(self) -> datetime:
            return self._clock.now()

In tests:
    from unittest.mock import MagicMock
    fixed = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    clock = MagicMock(spec=Clock)
    clock.now.return_value = fixed
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Protocol for injectable time source."""

    def now(self) -> datetime:
        """Returns the current UTC time as a timezone-aware datetime."""
        ...


class SystemClock:
    """
    Production clock — returns real UTC time.
    This is the default injected into all service classes.
    """

    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class FixedClock:
    """
    Test clock — always returns the same fixed time.
    Use in unit tests to make time-dependent logic deterministic.

    Example:
        clock = FixedClock(datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc))
        assert clock.now().year == 2026
    """

    def __init__(self, fixed_time: datetime) -> None:
        if fixed_time.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._time = fixed_time

    def now(self) -> datetime:
        return self._time
