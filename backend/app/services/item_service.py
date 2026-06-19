"""
ReceiptSplit — Item Service

Manages line items: CRUD, claims, and unclaims.
All mutations write audit rows to receipt_edits (DB-3).
All mutations use CAS versioning (TXN-1) and two-phase events (TXN-2).

Design authority:
    - PDD §6 (Line Items)
    - PDD §7 (Claiming)
    - Phase 1 Design Amendments TXN-1, TXN-2, DB-3
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.domain.claim_validator import ClaimValidator
from app.models.line_item import LineItem
from app.models.line_item_assignment import LineItemAssignment
from app.shared.errors import (
    DomainError,
    ItemNotFound,
    VersionConflict,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.interfaces.assignment import AssignmentRepository
    from app.repositories.interfaces.item import ItemRepository
    from app.repositories.interfaces.receipt_edit import ReceiptEditRepository
    from app.repositories.interfaces.room import RoomRepository
    from app.services.event_publisher import EventPublisher

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

    # ── CRUD ──────────────────────────────────────────────────────────────────

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
        """Create a new line item. Records audit trail."""
        item = LineItem(
            receipt_id=receipt_id,
            name=name,
            quantity=quantity,
            total_paise=total_paise,
        )

        async with db.begin():
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
                db, room_id, "item.created", actor_id,
                {"item_id": str(item.id), "name": name},
            )
            await db.refresh(item)

        await self._events.broadcast(
            room_id, "item.created", {"item_id": str(item.id), "name": name}, seq
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
        """
        CAS update on item fields. Writes receipt_edit per changed field.
        """
        # Read old values for audit
        old_item = await self._item_repo.get(db, item_id)
        if old_item is None or old_item.deleted_at is not None:
            raise ItemNotFound()

        async with db.begin():
            updated = await self._item_repo.update(
                db, item_id, expected_version, changes
            )
            if not updated:
                raise VersionConflict()

            # Audit each changed field
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
                db, room_id, "item.updated", actor_id,
                {"item_id": str(item_id), "fields": list(changes.keys())},
            )

        await self._events.broadcast(
            room_id, "item.updated",
            {"item_id": str(item_id), "fields": list(changes.keys())}, seq
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
        """Soft-delete a line item. CAS-guarded."""
        old_item = await self._item_repo.get(db, item_id)
        if old_item is None or old_item.deleted_at is not None:
            raise ItemNotFound()

        async with db.begin():
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
                db, room_id, "item.deleted", actor_id,
                {"item_id": str(item_id), "name": old_item.name},
            )

        await self._events.broadcast(
            room_id, "item.deleted",
            {"item_id": str(item_id), "name": old_item.name}, seq
        )

    # ── Claims ────────────────────────────────────────────────────────────────

    async def claim_item(
        self,
        db: AsyncSession,
        room_id: UUID,
        item_id: UUID,
        item_version: int,
        participant_id: UUID,
        claimed_qty: int,
    ) -> LineItemAssignment:
        """
        Claim units of an item for a participant.

        1. Validate room is active and item_wise mode.
        2. CAS version bump on item (TXN-1).
        3. Validate quantity available.
        4. Insert assignment.
        5. Append event in-tx (TXN-2).
        6. Broadcast post-commit.
        """
        # Pre-checks using ClaimValidator
        room = await self._room_repo.get_by_id(db, room_id)
        if room is None:
            raise DomainError(code="ROOM_NOT_FOUND", message="Room not found.")
        
        ClaimValidator.validate_room_active(room.status)
        ClaimValidator.validate_item_wise_mode(room.split_mode)

        item = await self._item_repo.get(db, item_id)
        if item is None or item.deleted_at is not None:
            raise ItemNotFound()

        async with db.begin():
            # CAS version bump — prevents concurrent claim races
            updated = await self._item_repo.update(
                db, item_id, item_version, {}
            )
            if not updated:
                raise VersionConflict()

            # Check remaining quantity
            already_claimed = await self._assignment_repo.get_claimed_qty(db, item_id)
            ClaimValidator.validate_quantity_available(
                claimed_qty=claimed_qty,
                item_qty=item.quantity,
                already_claimed=already_claimed,
            )

            # Insert assignment
            assignment = LineItemAssignment(
                room_id=room_id,
                line_item_id=item_id,
                participant_id=participant_id,
                claimed_qty=claimed_qty,
            )
            await self._assignment_repo.create(db, assignment)
            await db.flush()

            seq = await self._events.append_in_tx(
                db, room_id, "claim.created", participant_id,
                {
                    "item_id": str(item_id),
                    "claimed_qty": claimed_qty,
                    "assignment_id": str(assignment.id),
                },
            )

        await self._events.broadcast(
            room_id, "claim.created",
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
        """
        Remove a participant's claim on an item.

        1. Validate ownership (delete returns False if no row).
        2. Append event in-tx.
        3. Broadcast post-commit.
        """
        async with db.begin():
            deleted = await self._assignment_repo.delete_by_participant_and_item(
                db, item_id, participant_id
            )
            if not deleted:
                raise DomainError(
                    code="CLAIM_NOT_FOUND",
                    message="You don't have a claim on this item.",
                )

            seq = await self._events.append_in_tx(
                db, room_id, "claim.deleted", participant_id,
                {"item_id": str(item_id)},
            )

        await self._events.broadcast(
            room_id, "claim.deleted",
            {"item_id": str(item_id), "participant_id": str(participant_id)},
            seq,
        )
