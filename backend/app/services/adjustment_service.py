"""
ReceiptSplit — Adjustment Service

Manages split adjustments (tax, service charge, delivery fee, discount).
All mutations write audit rows (DB-3) and follow TXN-1/TXN-2.

Design authority:
    - PDD §8 (Adjustments)
    - Phase 1 Design Amendments DB-3, DB-4, TXN-1, TXN-2
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.domain.adjustments import is_percentage_allowed, normalize_stored_amount
from app.models.split_adjustment import SplitAdjustment
from app.shared.errors import DomainError, VersionConflict

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.interfaces.adjustment import AdjustmentRepository
    from app.repositories.interfaces.receipt_edit import ReceiptEditRepository
    from app.repositories.interfaces.room import RoomRepository
    from app.services.event_publisher import EventPublisher

if True:
    pass

logger = logging.getLogger(__name__)


class AdjustmentService:
    def __init__(
        self,
        adjustment_repo: AdjustmentRepository,
        receipt_edit_repo: ReceiptEditRepository,
        room_repo: RoomRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._adj_repo = adjustment_repo
        self._edit_repo = receipt_edit_repo
        self._room_repo = room_repo
        self._events = event_publisher

    async def add_adjustment(
        self,
        db: AsyncSession,
        room_id: UUID,
        receipt_id: UUID,
        actor_id: UUID,
        adj_type: str,
        label: str,
        amount_paise: int,
        allocation_method: str = "proportional",
        rate_basis_points: int | None = None,
        sort_order: int = 0,
    ) -> SplitAdjustment:
        """Create a new adjustment. Records audit trail."""
        if rate_basis_points is not None and not is_percentage_allowed(adj_type):
            raise DomainError(
                code="INVALID_ADJUSTMENT_AMOUNT",
                message="Rounding adjustments must use a flat amount.",
            )
        stored_amount = 0 if rate_basis_points is not None else normalize_stored_amount(
            adj_type, amount_paise
        )
        adj = SplitAdjustment(
            room_id=room_id,
            type=adj_type,
            label=label,
            amount_paise=stored_amount,
            rate_basis_points=rate_basis_points,
            allocation_method=allocation_method,
            sort_order=sort_order,
        )

        async with db.begin_nested():
            room = await self._room_repo.fetch_optional(db, room_id)
            if room is None or room.status not in ("draft", "active"):
                raise DomainError(
                    code="INVALID_STATE_TRANSITION",
                    message="Room is no longer open for edits.",
                )

            await self._adj_repo.create(db, adj)
            await db.flush()

            await self._edit_repo.append_in_tx(
                db,
                receipt_id=receipt_id,
                participant_id=actor_id,
                field="adjustment.created",
                old_value=None,
                new_value=f'{{"type":"{adj_type}","label":"{label}","amount_paise":{stored_amount},"rate_basis_points":{rate_basis_points or 0}}}',
            )

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "adjustment.created",
                actor_id,
                {"adjustment_id": str(adj.id), "type": adj_type, "label": label},
            )
            await db.refresh(adj)

        await self._events.broadcast(
            room_id,
            "adjustment.created",
            {"adjustment_id": str(adj.id), "type": adj_type, "label": label},
            seq,
        )
        return adj

    async def update_adjustment(
        self,
        db: AsyncSession,
        adjustment_id: UUID,
        room_id: UUID,
        receipt_id: UUID,
        expected_version: int,
        actor_id: UUID,
        changes: dict[str, Any],
    ) -> None:
        """CAS update on adjustment fields. Writes receipt_edit per changed field."""
        # Build the CAS update fields (map to DB columns)
        update_fields: dict[str, Any] = {}
        for key, value in changes.items():
            if key in ("label", "amount_paise", "rate_basis_points", "allocation_method"):
                update_fields[key] = value

        if not update_fields:
            raise DomainError(code="NO_CHANGES", message="No valid fields to update.")

        async with db.begin_nested():
            room = await self._room_repo.fetch_optional(db, room_id)
            if room is None or room.status not in ("draft", "active"):
                raise DomainError(
                    code="INVALID_STATE_TRANSITION",
                    message="Room is no longer open for edits.",
                )

            adjustment = next(
                (
                    current
                    for current in await self._adj_repo.list_by_room(db, room_id)
                    if current.id == adjustment_id
                ),
                None,
            )
            if adjustment is None:
                raise VersionConflict()

            if update_fields.get("rate_basis_points") is not None and not is_percentage_allowed(
                adjustment.type
            ):
                raise DomainError(
                    code="INVALID_ADJUSTMENT_AMOUNT",
                    message="Rounding adjustments must use a flat amount.",
                )

            if "rate_basis_points" in update_fields:
                update_fields["amount_paise"] = 0

            if "amount_paise" in update_fields:
                update_fields["amount_paise"] = normalize_stored_amount(
                    adjustment.type, update_fields["amount_paise"]
                )

            updated = await self._adj_repo.update(
                db, adjustment_id, expected_version, update_fields
            )
            if not updated:
                raise VersionConflict()

            for field_name, new_value in changes.items():
                await self._edit_repo.append_in_tx(
                    db,
                    receipt_id=receipt_id,
                    participant_id=actor_id,
                    field=f"adjustment.{field_name}",
                    old_value=None,  # we don't pre-read adjustment for simplicity
                    new_value=str(new_value),
                )

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "adjustment.updated",
                actor_id,
                {"adjustment_id": str(adjustment_id), "fields": list(changes.keys())},
            )

        await self._events.broadcast(
            room_id,
            "adjustment.updated",
            {"adjustment_id": str(adjustment_id), "fields": list(changes.keys())},
            seq,
        )

    async def delete_adjustment(
        self,
        db: AsyncSession,
        adjustment_id: UUID,
        room_id: UUID,
        receipt_id: UUID,
        expected_version: int,
        actor_id: UUID,
    ) -> None:
        """Soft-delete an adjustment. CAS-guarded."""
        async with db.begin_nested():
            room = await self._room_repo.fetch_optional(db, room_id)
            if room is None or room.status not in ("draft", "active"):
                raise DomainError(
                    code="INVALID_STATE_TRANSITION",
                    message="Room is no longer open for edits.",
                )

            deleted = await self._adj_repo.soft_delete(db, adjustment_id, expected_version)
            if not deleted:
                raise VersionConflict()

            await self._edit_repo.append_in_tx(
                db,
                receipt_id=receipt_id,
                participant_id=actor_id,
                field="adjustment.deleted",
                old_value=str(adjustment_id),
                new_value=None,
            )

            seq = await self._events.append_in_tx(
                db,
                room_id,
                "adjustment.deleted",
                actor_id,
                {"adjustment_id": str(adjustment_id)},
            )

        await self._events.broadcast(
            room_id,
            "adjustment.deleted",
            {"adjustment_id": str(adjustment_id)},
            seq,
        )
