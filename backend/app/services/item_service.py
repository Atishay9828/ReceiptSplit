"""ReceiptSplit item service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.domain.claim_validator import ClaimValidator
from app.models.line_item import LineItem
from app.models.line_item_assignment import LineItemAssignment
from app.shared.errors import DomainError, ItemNotFound, VersionConflict

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.interfaces.assignment import AssignmentRepository
    from app.repositories.interfaces.item import ItemRepository
    from app.repositories.interfaces.receipt_edit import ReceiptEditRepository
    from app.repositories.interfaces.room import RoomRepository
    from app.services.event_publisher import EventPublisher

if True:
    pass

logger = logging.getLogger(__name__)


class ItemService:
    def __init__(
        self,
        item_repo: ItemRepository,
        assignment_repo: AssignmentRepository,
        receipt_edit_repo: ReceiptEditRepository,
        room_repo: RoomRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._item_repo = item_repo
        self._assignment_repo = assignment_repo
        self._edit_repo = receipt_edit_repo
        self._room_repo = room_repo
        self._events = event_publisher

    async def add_item(
        self,
        db: AsyncSession,
        receipt_id: UUID,
        room_id: UUID,
        actor_id: UUID,
        name: str,
        quantity: int,
        total_paise: int,
    ) -> LineItem:
        """Create a new line item and record audit/event rows."""
        item = LineItem(
            receipt_id=receipt_id,
            name=name,
            quantity=quantity,
            total_paise=total_paise,
        )

        async with db.begin_nested():
            room = await self._room_repo.fetch_optional(db, room_id)
            if room is None or room.status not in ("draft", "active"):
                raise DomainError(
                    code="INVALID_STATE_TRANSITION",
                    message="Room is no longer open for edits.",
                )

            await self._item_repo.create(db, item)
            await db.flush()

            await self._edit_repo.append_in_tx(
                db,
                receipt_id=receipt_id,
                participant_id=actor_id,
                field="item.created",
                old_value=None,
                new_value=f'{{"name":"{name}","qty":{quantity},"total_paise":{total_paise}}}',
            )

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "item.created",
                actor_id,
                {"item_id": str(item.id), "name": name},
            )
            await db.refresh(item)

        await self._events.broadcast(
            room_id,
            "item.created",
            {"item_id": str(item.id), "name": name},
            seq,
        )
        return item

    async def update_item(
        self,
        db: AsyncSession,
        item_id: UUID,
        room_id: UUID,
        receipt_id: UUID,
        expected_version: int,
        actor_id: UUID,
        changes: dict[str, Any],
    ) -> None:
        """CAS update item fields and record audit/event rows."""
        async with db.begin_nested():
            room = await self._room_repo.fetch_optional(db, room_id)
            if room is None or room.status not in ("draft", "active"):
                raise DomainError(
                    code="INVALID_STATE_TRANSITION",
                    message="Room is no longer open for edits.",
                )

            old_item = await self._item_repo.fetch_optional(db, item_id)
            if old_item is None or old_item.deleted_at is not None:
                raise ItemNotFound()

            updated = await self._item_repo.update(db, item_id, expected_version, changes)
            if not updated:
                raise VersionConflict()

            for field_name, new_value in changes.items():
                old_value = getattr(old_item, field_name, None)
                await self._edit_repo.append_in_tx(
                    db,
                    receipt_id=receipt_id,
                    participant_id=actor_id,
                    field=f"item.{field_name}",
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value),
                )

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "item.updated",
                actor_id,
                {"item_id": str(item_id), "fields": list(changes.keys())},
            )

        await self._events.broadcast(
            room_id,
            "item.updated",
            {"item_id": str(item_id), "fields": list(changes.keys())},
            seq,
        )

    async def delete_item(
        self,
        db: AsyncSession,
        item_id: UUID,
        room_id: UUID,
        receipt_id: UUID,
        expected_version: int,
        actor_id: UUID,
    ) -> None:
        """Soft-delete a line item with CAS protection."""
        async with db.begin_nested():
            room = await self._room_repo.fetch_optional(db, room_id)
            if room is None or room.status not in ("draft", "active"):
                raise DomainError(
                    code="INVALID_STATE_TRANSITION",
                    message="Room is no longer open for edits.",
                )

            old_item = await self._item_repo.fetch_optional(db, item_id)
            if old_item is None or old_item.deleted_at is not None:
                raise ItemNotFound()

            deleted = await self._item_repo.soft_delete(db, item_id, expected_version)
            if not deleted:
                raise VersionConflict()

            await self._edit_repo.append_in_tx(
                db,
                receipt_id=receipt_id,
                participant_id=actor_id,
                field="item.deleted",
                old_value=f'{{"name":"{old_item.name}","total_paise":{old_item.total_paise}}}',
                new_value=None,
            )

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "item.deleted",
                actor_id,
                {"item_id": str(item_id), "name": old_item.name},
            )

        await self._events.broadcast(
            room_id,
            "item.deleted",
            {"item_id": str(item_id), "name": old_item.name},
            seq,
        )

    async def claim_item(
        self,
        db: AsyncSession,
        room_id: UUID,
        item_id: UUID,
        item_version: int,
        participant_id: UUID,
        claimed_qty: int,
    ) -> LineItemAssignment:
        """Claim units of an item for a participant."""
        async with db.begin_nested():
            room = await self._room_repo.get_by_id(db, room_id)
            if room is None:
                raise DomainError(code="ROOM_NOT_FOUND", message="Room not found.")

            ClaimValidator.validate_room_active(room.status)
            ClaimValidator.validate_item_wise_mode(room.split_mode)

            item = await self._item_repo.fetch_optional(db, item_id)
            if item is None or item.deleted_at is not None:
                raise ItemNotFound()

            updated = await self._item_repo.update(db, item_id, item_version, {})
            if not updated:
                raise VersionConflict()

            already_claimed = await self._assignment_repo.get_claimed_qty(db, item_id)
            ClaimValidator.validate_quantity_available(
                claimed_qty=claimed_qty,
                item_qty=item.quantity,
                already_claimed=already_claimed,
            )

            assignment = LineItemAssignment(
                room_id=room_id,
                line_item_id=item_id,
                participant_id=participant_id,
                claimed_qty=claimed_qty,
            )
            await self._assignment_repo.create(db, assignment)
            await db.flush()

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "claim.created",
                participant_id,
                {
                    "item_id": str(item_id),
                    "claimed_qty": claimed_qty,
                    "assignment_id": str(assignment.id),
                },
            )

        await self._events.broadcast(
            room_id,
            "claim.created",
            {"item_id": str(item_id), "claimed_qty": claimed_qty},
            seq,
        )
        return assignment

    async def unclaim_item(
        self,
        db: AsyncSession,
        room_id: UUID,
        item_id: UUID,
        participant_id: UUID,
    ) -> None:
        """Remove a participant's claim on an item."""
        async with db.begin_nested():
            deleted = await self._assignment_repo.delete_by_participant_and_item(
                db, item_id, participant_id
            )
            if not deleted:
                raise DomainError(
                    code="CLAIM_NOT_FOUND",
                    message="You don't have a claim on this item.",
                )

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "claim.deleted",
                participant_id,
                {"item_id": str(item_id)},
            )

        await self._events.broadcast(
            room_id,
            "claim.deleted",
            {"item_id": str(item_id), "participant_id": str(participant_id)},
            seq,
        )
