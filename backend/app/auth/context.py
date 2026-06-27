from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID


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
