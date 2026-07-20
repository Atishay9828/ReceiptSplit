from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from app.auth.context import (
    AuthenticatedUser,
    ParticipantAuthContext,
    RequestAuthContext,
    authenticated_user_from_claims,
    classify_bearer_token,
    parse_bearer_authorization,
)
from app.auth.dependencies import (
    require_authenticated_user,
    resolve_request_auth_context,
)
from app.auth.errors import InvalidJwt, UserAuthRequired
from app.auth.jwt import FakeJwtVerifier, JwtClaims
from app.auth.tokens import hash_token


def _jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "none", "typ": "JWT"}
    encoded_parts = []
    for part in (header, payload):
        raw = json.dumps(part, separators=(",", ":")).encode("utf-8")
        encoded_parts.append(base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii"))
    return f"{encoded_parts[0]}.{encoded_parts[1]}.dev-signature"


class _Result:
    def __init__(self, row: SimpleNamespace | None) -> None:
        self._row = row

    def first(self) -> SimpleNamespace | None:
        return self._row


class _Db:
    def __init__(self, token: str, role: str) -> None:
        self.participant_id = uuid4()
        self.room_id = uuid4()
        self.expected_hash = hash_token(token)
        self.executed_hash: str | None = None
        self.role = role

    async def execute(self, _statement: Any, params: dict[str, str]) -> _Result:
        self.executed_hash = params["token_hash"]
        if self.executed_hash != self.expected_hash:
            return _Result(None)
        return _Result(
            SimpleNamespace(
                id=self.participant_id,
                room_id=self.room_id,
                role=self.role,
            )
        )


class _ExplodingDb:
    async def execute(self, _statement: Any, _params: dict[str, str]) -> _Result:
        raise AssertionError("JWT auth must not query capability token storage")


def test_parse_bearer_authorization_accepts_bearer_header() -> None:
    assert parse_bearer_authorization("Bearer abc.def.ghi") == "abc.def.ghi"


@pytest.mark.parametrize("header", ["", "Token abc", "Bearer", "Bearer   "])
def test_parse_bearer_authorization_rejects_malformed_header(header: str) -> None:
    with pytest.raises(ValueError):
        parse_bearer_authorization(header)


@pytest.mark.parametrize("token", ["rs_pt_abc123", "rs_cr_abc123"])
def test_classify_bearer_token_keeps_capability_tokens_separate(token: str) -> None:
    assert classify_bearer_token(token) == "capability"


def test_classify_bearer_token_identifies_jwt_shape() -> None:
    assert classify_bearer_token(_jwt({"sub": "user-123"})) == "jwt"


def test_authenticated_user_from_claims_uses_stable_claim_identity() -> None:
    claims = JwtClaims(provider="dev", subject="user-123", email="aj@example.com")

    first = authenticated_user_from_claims(claims)
    second = authenticated_user_from_claims(claims)

    assert first == AuthenticatedUser(
        id=UUID(str(first.id)),
        provider="dev",
        subject="user-123",
        email="aj@example.com",
    )
    assert second.id == first.id


@pytest.mark.asyncio
async def test_resolve_request_auth_context_resolves_participant_capability_token() -> None:
    token = "rs_pt_test-token"
    db = _Db(token=token, role="participant")
    verifier = FakeJwtVerifier({})

    ctx = await resolve_request_auth_context(f"Bearer {token}", cast("Any", db), verifier)

    assert ctx.user is None
    assert ctx.participant == ParticipantAuthContext(
        participant_id=db.participant_id,
        room_id=db.room_id,
        role="participant",
    )
    assert db.executed_hash == db.expected_hash


@pytest.mark.asyncio
async def test_resolve_request_auth_context_resolves_creator_capability_token() -> None:
    token = "rs_cr_test-token"
    db = _Db(token=token, role="creator")
    verifier = FakeJwtVerifier({})

    ctx = await resolve_request_auth_context(f"Bearer {token}", cast("Any", db), verifier)

    assert ctx.participant is not None
    assert ctx.participant.is_creator is True
    assert ctx.user is None


@pytest.mark.asyncio
async def test_resolve_request_auth_context_resolves_user_jwt_without_capability_lookup() -> None:
    token = _jwt({"sub": "user-123"})
    verifier = FakeJwtVerifier({token: JwtClaims(provider="dev", subject="user-123")})

    ctx = await resolve_request_auth_context(
        f"Bearer {token}", cast("Any", _ExplodingDb()), verifier
    )

    assert ctx.participant is None
    assert ctx.user == authenticated_user_from_claims(
        JwtClaims(provider="dev", subject="user-123")
    )


@pytest.mark.asyncio
async def test_malformed_jwt_returns_invalid_jwt_error() -> None:
    token = "not.a.valid-jwt"
    verifier = FakeJwtVerifier({})

    with pytest.raises(InvalidJwt):
        await resolve_request_auth_context(
            f"Bearer {token}", cast("Any", _ExplodingDb()), verifier
        )


@pytest.mark.asyncio
async def test_participant_context_cannot_satisfy_user_only_auth() -> None:
    ctx = RequestAuthContext(
        participant=ParticipantAuthContext(
            participant_id=uuid4(),
            room_id=uuid4(),
            role="participant",
        )
    )

    with pytest.raises(UserAuthRequired):
        await require_authenticated_user(ctx)
