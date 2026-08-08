from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room_participant import RoomParticipant


class ParticipantRepository(Protocol):
    async def get_by_room_user(
        self, db: AsyncSession, room_id: UUID, user_id: UUID
    ) -> RoomParticipant | None: ...

    async def join_room_in_tx(
        self,
        db: AsyncSession,
        room_id: UUID,
        invite_token_hash: str,
        nickname: str,
        color: str,
        new_token_hash: str,
        user_id: UUID | None = None,
    ) -> RoomParticipant:
        """
        Atomically joins an account-backed participant. Serializes concurrent joins via
        advisory lock and refreshes the capability token when the same account rejoins.
        Must be called within a transaction.
        """
        ...

    async def get_by_token(self, db: AsyncSession, token_hash: str) -> RoomParticipant | None:
        """Retrieves a participant by their token hash."""
        ...

    async def list_active(self, db: AsyncSession, room_id: UUID) -> list[RoomParticipant]:
        """Lists all active participants for a room (where left_at IS NULL)."""
        ...
