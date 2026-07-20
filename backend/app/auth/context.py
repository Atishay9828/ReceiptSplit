from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import NAMESPACE_URL, uuid5

if TYPE_CHECKING:
    from uuid import UUID

    from app.auth.jwt import JwtClaims

BearerTokenKind = Literal["capability", "jwt"]


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Resolved OIDC/JWT user identity."""

    id: UUID
    provider: str
    subject: str
    email: str | None = None


@dataclass(frozen=True, slots=True)
class ParticipantAuthContext:
    """Resolved room capability-token identity."""

    participant_id: UUID
    room_id: UUID
    role: str

    @property
    def is_creator(self) -> bool:
        return self.role == "creator"

    @property
    def is_participant(self) -> bool:
        return self.role == "participant"


@dataclass(frozen=True, slots=True)
class RequestAuthContext:
    """Request identity container that keeps user JWT and capability auth separate."""

    user: AuthenticatedUser | None = None
    participant: ParticipantAuthContext | None = None

    @property
    def has_user(self) -> bool:
        return self.user is not None

    @property
    def has_participant(self) -> bool:
        return self.participant is not None


AuthContext = ParticipantAuthContext


def parse_bearer_authorization(authorization_header: str) -> str:
    """Extract the token from an Authorization: Bearer <token> header."""
    parts = authorization_header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Authorization header must be 'Bearer <token>'")
    return parts[1]


def classify_bearer_token(token: str) -> BearerTokenKind:
    """Classify bearer credentials without treating token prefixes as proof."""
    if token.startswith(("rs_cr_", "rs_pt_")):
        return "capability"
    if token.count(".") == 2:
        return "jwt"
    return "capability"


def authenticated_user_from_claims(claims: JwtClaims) -> AuthenticatedUser:
    """Create ReceiptSplit's stable local user identity from verified JWT claims."""
    user_id = uuid5(NAMESPACE_URL, f"receiptsplit:user:{claims.provider}:{claims.subject}")
    return AuthenticatedUser(
        id=user_id,
        provider=claims.provider,
        subject=claims.subject,
        email=claims.email,
    )
