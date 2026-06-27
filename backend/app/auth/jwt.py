from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class JwtClaims:
    """Provider-normalized claims accepted by ReceiptSplit auth."""

    provider: str
    subject: str
    email: str | None = None


class JwtVerifier(Protocol):
    """Verifies a bearer JWT and returns normalized identity claims."""

    async def verify(self, token: str) -> JwtClaims:
        ...
