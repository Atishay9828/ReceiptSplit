from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.shared.errors import RateLimitExceeded

if TYPE_CHECKING:
    from fastapi import Request


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    limit: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = {}

    def reset(self) -> None:
        self._buckets.clear()

    def hit(self, key: str, rule: RateLimitRule) -> bool:
        now = time.monotonic()
        cutoff = now - rule.window_seconds
        attempts = [seen_at for seen_at in self._buckets.get(key, []) if seen_at >= cutoff]
        if len(attempts) >= rule.limit:
            self._buckets[key] = attempts
            return False
        attempts.append(now)
        self._buckets[key] = attempts
        return True


limiter = InMemoryRateLimiter()


def client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    action: str,
    key_parts: list[str],
    rule: RateLimitRule,
) -> None:
    key = "|".join([action, *key_parts])
    if not limiter.hit(key, rule):
        raise RateLimitExceeded()
