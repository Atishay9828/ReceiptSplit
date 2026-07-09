"""
ReceiptSplit — Room Service

Orchestrates room lifecycle: creation, updates, and state transitions.
Delegates state machine validation to app.domain.room_state_machine.

Design authority:
    - PDD §3 (Room Lifecycle)
    - Phase 1 Design Amendments TXN-1, TXN-2
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from app.auth.tokens import (
    generate_creator_token,
    generate_invite_token,
    hash_token,
)
from app.domain import room_state_machine
from app.models.receipt import Receipt
from app.models.room import Room
from app.models.room_invite import RoomInvite
from app.models.room_participant import RoomParticipant
from app.shared.clock import SystemClock
from app.shared.errors import RoomNotFound, VersionConflict

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.interfaces.participant import ParticipantRepository
    from app.repositories.interfaces.receipt import ReceiptRepository
    from app.repositories.interfaces.room import RoomRepository
    from app.services.audit_service import AuditService
    from app.services.event_publisher import EventPublisher

if True:
    pass

logger = logging.getLogger(__name__)


class RoomService:
    def __init__(
        self,
        room_repo: RoomRepository,
        receipt_repo: ReceiptRepository,
        participant_repo: ParticipantRepository,
        event_publisher: EventPublisher,
        audit_service: AuditService | None = None,
    ) -> None:
        self._room_repo = room_repo
        self._receipt_repo = receipt_repo
        self._participant_repo = participant_repo
        self._events = event_publisher
        self._audit = audit_service

    async def create_room(
        self,
        db: AsyncSession,
        split_mode: str = "equal",
        payer_name: str | None = None,
        payer_vpa: str | None = None,
        room_ttl_days: int = 30,
    ) -> tuple[Room, str, str]:
        """
        Create a new room with receipt, creator invite, and creator participant.

        Returns:
            (room, raw_creator_token, raw_invite_token)
        """
        now = SystemClock().now()

        # -- Room --
        room = Room(
            status="draft",
            split_mode=split_mode,
            payer_name=payer_name,
            payer_vpa=payer_vpa,
            expires_at=now + timedelta(days=room_ttl_days),
        )
        async with db.begin_nested():
            await self._room_repo.create(db, room)
            await db.flush()

            # -- Receipt --
            receipt = Receipt(room_id=room.id, source="manual", is_replaceable=True)
            await self._receipt_repo.create(db, receipt)
            await db.flush()

            # -- Creator invite --
            raw_invite_token = generate_invite_token()
            invite = RoomInvite(
                room_id=room.id,
                token_hash=hash_token(raw_invite_token),
                type="creator",
            )
            db.add(invite)
            await db.flush()

            # -- Creator participant --
            raw_creator_token = generate_creator_token()
            participant = RoomParticipant(
                room_id=room.id,
                invite_id=invite.id,
                nickname=payer_name or "Creator",
                color="#4F46E5",
                role="creator",
                token_hash=hash_token(raw_creator_token),
            )
            db.add(participant)
            await db.flush()

            # -- Event --
            seq = await self._events.append_in_tx(
                db,
                room.id,
                "room.created",
                actor_id=participant.id,
                payload={"split_mode": split_mode},
            )
            if self._audit is not None:
                await self._audit.record(
                    db,
                    action="room.created",
                    room_id=room.id,
                    actor_participant_id=participant.id,
                    actor_type="creator",
                    metadata={"split_mode": split_mode},
                )
            await db.refresh(room)

        await self._events.broadcast(room.id, "room.created", {"split_mode": split_mode}, seq)

        return room, raw_creator_token, raw_invite_token

    async def get_room(self, db: AsyncSession, room_id: UUID) -> Room:
        """Fetch a room by ID. Raises RoomNotFound if missing."""
        room = await self._room_repo.get_by_id(db, room_id)
        if room is None:
            raise RoomNotFound()
        return room

    async def get_receipt(self, db: AsyncSession, room_id: UUID) -> Receipt:
        """Fetch the room's receipt. Rooms are created with exactly one receipt."""
        receipt = await self._receipt_repo.get_by_room(db, room_id)
        if receipt is None:
            raise RoomNotFound()
        return receipt

    async def update_room(
        self,
        db: AsyncSession,
        room_id: UUID,
        expected_version: int,
        actor_id: UUID,
        update_fields: dict[str, Any],
    ) -> Room:
        """
        CAS update on room fields (split_mode, payer_vpa, payer_name, etc.).
        Raises VersionConflict if stale.
        """
        async with db.begin_nested():
            updated = await self._room_repo.update(db, room_id, expected_version, update_fields)
            if not updated:
                raise VersionConflict()

            if update_fields.get("payer_name"):
                participants = await self._participant_repo.list_active(db, room_id)
                for participant in participants:
                    if participant.role == "creator":
                        participant.nickname = str(update_fields["payer_name"])
                        break

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "room.updated",
                actor_id=actor_id,
                payload={"fields": list(update_fields.keys())},
            )

        await self._events.broadcast(
            room_id, "room.updated", {"fields": list(update_fields.keys())}, seq
        )

        db.expire_all()
        return await self.get_room(db, room_id)

    async def transition_room(
        self,
        db: AsyncSession,
        room_id: UUID,
        expected_version: int,
        to_state: str,
        actor_id: UUID,
    ) -> Room:
        """
        Explicit state transition via the Room State Machine.
        Raises InvalidStateTransition if the move is illegal.
        Raises VersionConflict if stale.
        """
        async with db.begin_nested():
            room = await self.get_room(db, room_id)
            room_state_machine.validate_transition(room.status, to_state)

            updated = await self._room_repo.update(
                db, room_id, expected_version, {"status": to_state}
            )
            if not updated:
                raise VersionConflict()

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "room.state_changed",
                actor_id=actor_id,
                payload={"from": room.status, "to": to_state},
            )

        await self._events.broadcast(
            room_id,
            "room.state_changed",
            {"from": room.status, "to": to_state},
            seq,
        )

        db.expire_all()
        return await self.get_room(db, room_id)
