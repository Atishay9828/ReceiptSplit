from uuid import uuid4

from app.auth.context import (
    AuthenticatedUser,
    ParticipantAuthContext,
    RequestAuthContext,
)
from app.auth.jwt import JwtClaims, JwtVerifier
from app.config import Settings


class _Verifier:
    async def verify(self, token: str) -> JwtClaims:
        return JwtClaims(
            provider="dev",
            subject=token,
            email="aj@example.com",
        )


def test_authenticated_user_contract_is_stable() -> None:
    user_id = uuid4()

    user = AuthenticatedUser(
        id=user_id,
        provider="dev",
        subject="user-123",
        email="aj@example.com",
    )

    assert user.id == user_id
    assert user.provider == "dev"
    assert user.subject == "user-123"
    assert user.email == "aj@example.com"


def test_request_auth_context_keeps_user_and_capability_separate() -> None:
    participant_id = uuid4()
    room_id = uuid4()
    user = AuthenticatedUser(
        id=uuid4(),
        provider="dev",
        subject="owner",
        email=None,
    )
    participant = ParticipantAuthContext(
        participant_id=participant_id,
        room_id=room_id,
        role="participant",
    )

    ctx = RequestAuthContext(user=user, participant=participant)

    assert ctx.user == user
    assert ctx.participant == participant
    assert ctx.has_user is True
    assert ctx.has_participant is True
    assert participant.is_creator is False


def test_jwt_verifier_protocol_is_async() -> None:
    verifier: JwtVerifier = _Verifier()

    assert verifier is not None


def test_auth_config_names_exist() -> None:
    settings = Settings()

    assert settings.auth_oidc_provider == "dev"
    assert settings.auth_oidc_issuer is None
    assert settings.auth_oidc_audience is None
    assert settings.auth_jwks_url is None
