from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, text

from app.config import settings
from app.models.room_invite import RoomInvite
from app.models.room_participant import RoomParticipant
from app.repositories.interfaces.participant import ParticipantRepository
from app.repositories.postgres.base import PostgresRepository
from app.shared.errors import DomainError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

if True:
    pass


class PostgresParticipantRepository(PostgresRepository[RoomParticipant], ParticipantRepository):
    def __init__(self) -> None:
        super().__init__(RoomParticipant)

    async def join_room_in_tx(
        self,
        db: AsyncSession,
        room_id: UUID,
        invite_token_hash: str,
        nickname: str,
        color: str,
        new_token_hash: str,
    ) -> RoomParticipant:
        # Step 1: Acquire per-room advisory lock. (TXN-3)
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:room_id))"),
            {"room_id": str(room_id)},
        )

        # Step 2: Validate invite
        stmt = select(RoomInvite).where(
            RoomInvite.token_hash == invite_token_hash,
            RoomInvite.room_id == room_id,
            RoomInvite.revoked_at.is_(None),
        )
        result = await db.execute(stmt)
        invite = result.scalars().first()
        if not invite:
            raise DomainError(code="INVALID_TOKEN", message="This link is invalid or has expired.")

        # Step 3: Count active participants
        count_stmt = text("""
            SELECT COUNT(*) FROM room_participants
            WHERE room_id = :room_id AND left_at IS NULL
        """)
        count_result = await db.execute(count_stmt, {"room_id": str(room_id)})
        count = count_result.scalar()
        if count is not None and count >= settings.max_participants_per_room:
            raise DomainError(
                code="ROOM_FULL", message="This bill has reached the max of 20 people."
            )

        # Step 4: Insert participant
        participant = RoomParticipant(
            room_id=room_id,
            invite_id=invite.id,
            nickname=nickname,
            color=color,
            role="participant",
            token_hash=new_token_hash,
        )
        db.add(participant)
        return participant

    async def get_by_token(self, db: AsyncSession, token_hash: str) -> RoomParticipant | None:
        stmt = select(RoomParticipant).where(RoomParticipant.token_hash == token_hash)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_room_user(
        self, db: AsyncSession, room_id: UUID, user_id: UUID
    ) -> RoomParticipant | None:
        stmt = select(RoomParticipant).where(
            RoomParticipant.room_id == room_id,
            RoomParticipant.user_id == user_id,
            RoomParticipant.left_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_active(self, db: AsyncSession, room_id: UUID) -> list[RoomParticipant]:
        stmt = select(RoomParticipant).where(
            RoomParticipant.room_id == room_id, RoomParticipant.left_at.is_(None)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
