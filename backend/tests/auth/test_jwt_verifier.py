from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from app.auth.errors import InvalidJwt
from app.auth.jwt import DevJwtVerifier, FakeJwtVerifier, GoogleJwtVerifier, JwtClaims
from app.auth.provider import build_jwt_verifier
from app.config import Settings

pytestmark = pytest.mark.asyncio


def _jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "none", "typ": "JWT"}
    encoded_parts = []
    for part in (header, payload):
        raw = json.dumps(part, separators=(",", ":")).encode("utf-8")
        encoded_parts.append(base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii"))
    return f"{encoded_parts[0]}.{encoded_parts[1]}.dev-signature"


async def test_dev_jwt_verifier_returns_normalized_claims() -> None:
    verifier = DevJwtVerifier(provider="dev")

    claims = await verifier.verify(
        _jwt({"sub": "user-123", "email": "aj@example.com", "iss": "dev-issuer"})
    )

    assert claims == JwtClaims(
        provider="dev",
        subject="user-123",
        email="aj@example.com",
    )


async def test_dev_jwt_verifier_rejects_malformed_jwt() -> None:
    verifier = DevJwtVerifier(provider="dev")

    with pytest.raises(InvalidJwt):
        await verifier.verify("not-a-jwt")


async def test_dev_jwt_verifier_rejects_missing_subject() -> None:
    verifier = DevJwtVerifier(provider="dev")

    with pytest.raises(InvalidJwt):
        await verifier.verify(_jwt({"email": "aj@example.com"}))


async def test_dev_jwt_verifier_rejects_wrong_issuer_when_configured() -> None:
    verifier = DevJwtVerifier(provider="dev", issuer="expected-issuer")

    with pytest.raises(InvalidJwt):
        await verifier.verify(_jwt({"sub": "user-123", "iss": "other-issuer"}))


async def test_dev_jwt_verifier_rejects_wrong_audience_when_configured() -> None:
    verifier = DevJwtVerifier(provider="dev", audience="receiptsplit")

    with pytest.raises(InvalidJwt):
        await verifier.verify(_jwt({"sub": "user-123", "aud": "other-service"}))


async def test_fake_jwt_verifier_returns_registered_claims() -> None:
    claims = JwtClaims(provider="fake", subject="user-123", email=None)
    verifier = FakeJwtVerifier({"token": claims})

    assert await verifier.verify("token") == claims


async def test_fake_jwt_verifier_rejects_unknown_token() -> None:
    verifier = FakeJwtVerifier({})

    with pytest.raises(InvalidJwt):
        await verifier.verify("unknown")


async def test_google_provider_builds_signed_token_verifier() -> None:
    verifier = build_jwt_verifier(
        Settings(auth_oidc_provider="google", auth_oidc_audience="client.apps.googleusercontent.com")
    )

    assert verifier == GoogleJwtVerifier(audience="client.apps.googleusercontent.com")
