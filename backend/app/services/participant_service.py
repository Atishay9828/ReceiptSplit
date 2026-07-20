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
from app.shared.errors import InvalidColor
from app.shared.types import COLOR_PALETTE

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.room_participant import RoomParticipant
    from app.repositories.interfaces.assignment import AssignmentRepository
    from app.repositories.interfaces.participant import ParticipantRepository
    from app.repositories.interfaces.room import RoomRepository
    from app.services.audit_service import AuditService
    from app.services.event_publisher import EventPublisher


logger = logging.getLogger(__name__)


class ParticipantService:
    def __init__(
        self,
        participant_repo: ParticipantRepository,
        assignment_repo: AssignmentRepository,
        room_repo: RoomRepository,
        event_publisher: EventPublisher,
        audit_service: AuditService | None = None,
    ) -> None:
        self._participant_repo = participant_repo
        self._assignment_repo = assignment_repo
        self._room_repo = room_repo
        self._events = event_publisher
        self._audit = audit_service

    async def join_room(
        self,
        db: AsyncSession,
        room_id: UUID,
        invite_token_hash: str,
        nickname: str,
        color: str | None,
    ) -> tuple[RoomParticipant, str]:
        """
        Join a participant to a room.
        Uses advisory lock (TXN-3) to prevent the 20-participant race.

        Returns:
            (participant, raw_participant_token)
        """
        if color is not None and color not in COLOR_PALETTE:
            raise InvalidColor()

        raw_token = generate_participant_token()
        token_hash = hash_token(raw_token)

        async with db.begin_nested():
            if color is None:
                from app.shared.validators import pick_available_color

                active_participants = await self._participant_repo.list_active(db, room_id)
                used_colors = {p.color for p in active_participants}
                color = pick_available_color(used_colors)

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
            if self._audit is not None:
                await self._audit.record(
                    db,
                    action="participant.joined",
                    room_id=room_id,
                    participant_id=participant.id,
                    actor_participant_id=participant.id,
                    actor_type="participant",
                    metadata={"color": color},
                )

        await self._events.broadcast(
            room_id,
            "participant.joined",
            {"nickname": nickname, "color": color, "participant_id": str(participant.id)},
            seq,
        )

        return participant, raw_token

    async def list_active(self, db: AsyncSession, room_id: UUID) -> list[RoomParticipant]:
        """List all active (non-left) participants for a room."""
        return await self._participant_repo.list_active(db, room_id)

    async def get_by_token(self, db: AsyncSession, token_hash: str) -> RoomParticipant | None:
        """Look up a participant by their token hash."""
        return await self._participant_repo.get_by_token(db, token_hash)

    async def remove_participant(
        self,
        db: AsyncSession,
        room_id: UUID,
        participant_id: UUID,
        actor_id: UUID,
    ) -> None:
        """
        Removes a participant from a room.
        They must be in an active/draft room.
        Creator cannot be removed.
        Their item assignments are deleted.
        """
        from datetime import UTC, datetime

        from app.shared.errors import DomainError

        async with db.begin_nested():
            room = await self._room_repo.get_by_id(db, room_id)
            if room is None:
                raise DomainError(code="ROOM_NOT_FOUND", message="Room not found.")
            if room.status not in ["draft", "active"]:
                raise DomainError(
                    code="INVALID_STATE_TRANSITION",
                    message="Cannot remove participants after the room is locked.",
                )

            # Look up participant using list_active (since we want an active one)
            active_participants = await self._participant_repo.list_active(db, room_id)
            participant = next((p for p in active_participants if p.id == participant_id), None)

            if participant is None:
                raise DomainError(code="PARTICIPANT_NOT_FOUND", message="Participant not found.")
            if participant.role == "creator":
                raise DomainError(
                    code="CANNOT_REMOVE_CREATOR", message="Cannot remove the creator."
                )

            participant.left_at = datetime.now(UTC)

            # Delete their assignments
            await self._assignment_repo.delete_by_participant(db, participant_id)
            room.version += 1
            await db.flush()

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "participant.left",
                actor_id=actor_id,
                payload={"participant_id": str(participant.id)},
            )
            if self._audit is not None:
                await self._audit.record(
                    db,
                    action="participant.left",
                    room_id=room_id,
                    participant_id=participant.id,
                    actor_participant_id=actor_id,
                    actor_type="creator",
                    metadata={"removed": True},
                )

        await self._events.broadcast(
            room_id,
            "participant.left",
            {"participant_id": str(participant.id)},
            seq,
        )
