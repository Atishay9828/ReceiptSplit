"""
ReceiptSplit — Auth Context Model

`AuthContext` carries the resolved identity of the request caller.
It is produced by the `get_current_participant` dependency and consumed
by all route handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthContext:
    """
    Resolved authentication context for a single request.

    Attributes:
        participant_id: UUID of the authenticated room_participant row.
        room_id:        UUID of the room this participant belongs to.
        role:           'creator' or 'participant'.
    """

    participant_id: UUID
    room_id: UUID
    role: str

    @property
    def is_creator(self) -> bool:
        return self.role == "creator"

    @property
    def is_participant(self) -> bool:
        return self.role == "participant"
