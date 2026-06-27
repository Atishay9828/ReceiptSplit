from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from app.auth.errors import InvalidJwt

if TYPE_CHECKING:
    from collections.abc import Mapping


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


def _decode_base64url_json(value: str) -> dict[str, Any]:
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{value}{padding}")
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidJwt() from exc
    if not isinstance(payload, dict):
        raise InvalidJwt()
    return payload


@dataclass(frozen=True, slots=True)
class DevJwtVerifier:
    """Development verifier for unsigned JWT-shaped tokens in tests/local runs."""

    provider: str
    issuer: str | None = None
    audience: str | None = None

    async def verify(self, token: str) -> JwtClaims:
        parts = token.split(".")
        if len(parts) != 3 or not all(parts):
            raise InvalidJwt()

        payload = _decode_base64url_json(parts[1])
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise InvalidJwt()

        if self.issuer is not None and payload.get("iss") != self.issuer:
            raise InvalidJwt()

        if self.audience is not None and not self._audience_matches(payload.get("aud")):
            raise InvalidJwt()

        email = payload.get("email")
        return JwtClaims(
            provider=self.provider,
            subject=subject,
            email=email if isinstance(email, str) else None,
        )

    def _audience_matches(self, claim: Any) -> bool:
        if isinstance(claim, str):
            return claim == self.audience
        if isinstance(claim, list):
            return self.audience in claim
        return False


@dataclass(frozen=True, slots=True)
class FakeJwtVerifier:
    """Test verifier with explicit token-to-claims registration."""

    claims_by_token: Mapping[str, JwtClaims]

    async def verify(self, token: str) -> JwtClaims:
        claims = self.claims_by_token.get(token)
        if claims is None:
            raise InvalidJwt()
        return claims
