"""
ReceiptSplit — Participant Service

Handles participant join, listing, and lookup.
Join uses advisory lock via ParticipantRepository (TXN-3).

Design authority:
    - PDD §4 (Participant Lifecycle)
    - Phase 1 Design Amendments TXN-3
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.auth.tokens import generate_participant_token, hash_token

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.room_participant import RoomParticipant
    from app.repositories.interfaces.participant import ParticipantRepository
    from app.services.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class ParticipantService:
    def __init__(
        self,
        participant_repo: ParticipantRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._participant_repo = participant_repo
        self._events = event_publisher

    async def join_room(
        self,
        db: AsyncSession,
        room_id: UUID,
        invite_token_hash: str,
        nickname: str,
        color: str,
    ) -> tuple[RoomParticipant, str]:
        """
        Join a participant to a room.
        Uses advisory lock (TXN-3) to prevent the 20-participant race.

        Returns:
            (participant, raw_participant_token)
        """
        raw_token = generate_participant_token()
        token_hash = hash_token(raw_token)

        async with db.begin():
            participant = await self._participant_repo.join_room_in_tx(
                db,
                room_id=room_id,
                invite_token_hash=invite_token_hash,
                nickname=nickname,
                color=color,
                new_token_hash=token_hash,
            )
            await db.flush()

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "participant.joined",
                actor_id=participant.id,
                payload={"nickname": nickname, "color": color},
            )

        await self._events.broadcast(
            room_id,
            "participant.joined",
            {"nickname": nickname, "color": color, "participant_id": str(participant.id)},
            seq,
        )

        return participant, raw_token

    async def list_active(
        self, db: AsyncSession, room_id: UUID
    ) -> list[RoomParticipant]:
        """List all active (non-left) participants for a room."""
        return await self._participant_repo.list_active(db, room_id)

    async def get_by_token(
        self, db: AsyncSession, token_hash: str
    ) -> RoomParticipant | None:
        """Look up a participant by their token hash."""
        return await self._participant_repo.get_by_token(db, token_hash)
