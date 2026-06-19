"""
ReceiptSplit — Split Service

Decomposed into three responsibilities:
    SplitLockCoordinator  — lock/unlock workflow and transaction orchestration
    SplitSessionBuilder   — snapshot, build SplitInput, invoke engine, persist results
    SplitPreviewService   — read-only session retrieval

Design authority:
    - PDD §5 (Split Calculation)
    - Phase 1 Design Amendments DB-5, TXN-1, TXN-2
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.domain import room_state_machine
from app.models.participant_total import ParticipantTotal
from app.models.split_session import SplitSession
from app.shared.errors import (
    DomainError,
    InsufficientParticipants,
    NoItems,
    RoomAlreadyLocked,
    VersionConflict,
)
from app.split.calculator import SplitCalculator
from app.split.models import (
    SplitAdjustment as SplitAdjInput,
)
from app.split.models import (
    SplitAssignment,
    SplitInput,
    SplitItem,
    SplitParticipant,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.line_item import LineItem
    from app.models.room import Room
    from app.models.room_participant import RoomParticipant
    from app.models.split_adjustment import SplitAdjustment
    from app.repositories.interfaces.adjustment import AdjustmentRepository
    from app.repositories.interfaces.assignment import AssignmentRepository
    from app.repositories.interfaces.item import ItemRepository
    from app.repositories.interfaces.participant import ParticipantRepository
    from app.repositories.interfaces.receipt import ReceiptRepository
    from app.repositories.interfaces.room import RoomRepository
    from app.repositories.interfaces.split_session import SplitSessionRepository
    from app.services.event_publisher import EventPublisher
    from app.split.models import SplitResult

logger = logging.getLogger(__name__)


# ── SplitSessionBuilder ──────────────────────────────────────────────────────


class SplitSessionBuilder:
    """
    Pure computation + persistence.
    Snapshots adjustments, builds SplitInput, invokes engine, persists results.
    """

    @staticmethod
    def snapshot_adjustments(adjustments: list[SplitAdjustment]) -> list[dict]:
        """Serialize active adjustments to JSON for immutable snapshot (DB-5)."""
        return [
            {
                "id": str(a.id),
                "type": a.type,
                "label": a.label,
                "amount_paise": a.amount_paise,
                "allocation_method": a.allocation_method,
                "sort_order": a.sort_order,
            }
            for a in adjustments
        ]

    @staticmethod
    def build_split_input(
        mode: str,
        items: list[LineItem],
        participants: list[RoomParticipant],
        adjustments: list[SplitAdjustment],
        assignments: list,
    ) -> SplitInput:
        """Build the split engine's SplitInput from DB models."""
        split_items = [
            SplitItem(id=item.id, quantity=item.quantity, total_paise=item.total_paise)
            for item in items
        ]

        split_participants = []
        for i, p in enumerate(participants):
            split_participants.append(
                SplitParticipant(
                    id=p.id,
                    is_payer=(p.role == "creator"),
                    join_order=i,
                )
            )

        split_adjustments = [
            SplitAdjInput(
                type=a.type,
                amount_paise=a.amount_paise,
                allocation=a.allocation_method,
            )
            for a in adjustments
        ]

        split_assignments = [
            SplitAssignment(
                item_id=a.line_item_id,
                participant_id=a.participant_id,
                claimed_qty=a.claimed_qty,
                created_at=a.created_at,
            )
            for a in assignments
        ]

        return SplitInput(
            mode=mode,
            items=split_items,
            assignments=split_assignments,
            adjustments=split_adjustments,
            participants=split_participants,
        )

    @staticmethod
    async def persist_session(
        db: AsyncSession,
        session_repo: SplitSessionRepository,
        room: Room,
        result: SplitResult,
        snapshot: list[dict],
    ) -> SplitSession:
        """Create SplitSession and ParticipantTotal rows."""
        session = SplitSession(
            room_id=room.id,
            mode=room.split_mode,
            grand_total_paise=result.grand_total_paise,
            adjustments_snapshot=snapshot,
        )
        await session_repo.create(db, session)
        await db.flush()

        for bd in result.participant_totals:
            total = ParticipantTotal(
                split_session_id=session.id,
                participant_id=bd.participant_id,
                items_paise=bd.items_paise,
                discount_paise=bd.discount_paise,
                tax_paise=bd.tax_paise,
                service_charge_paise=bd.service_charge_paise,
                delivery_fee_paise=bd.delivery_fee_paise,
                adjustment_paise=bd.adjustment_paise,
                total_paise=bd.total_paise,
                is_payer=bd.is_payer,
            )
            db.add(total)

        return session


# ── SplitPreviewService ──────────────────────────────────────────────────────


class SplitPreviewService:
    """Read-only access to the current split session."""

    def __init__(self, session_repo: SplitSessionRepository) -> None:
        self._session_repo = session_repo

    async def get_current_session(
        self, db: AsyncSession, room_id: UUID
    ) -> SplitSession | None:
        return await self._session_repo.get_by_room(db, room_id)


# ── SplitLockCoordinator ─────────────────────────────────────────────────────


class SplitLockCoordinator:
    """
    Orchestrates the lock and unlock workflows.
    Transaction management lives here.
    """

    def __init__(
        self,
        room_repo: RoomRepository,
        receipt_repo: ReceiptRepository,
        item_repo: ItemRepository,
        participant_repo: ParticipantRepository,
        adjustment_repo: AdjustmentRepository,
        assignment_repo: AssignmentRepository,
        session_repo: SplitSessionRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._room_repo = room_repo
        self._receipt_repo = receipt_repo
        self._item_repo = item_repo
        self._participant_repo = participant_repo
        self._adj_repo = adjustment_repo
        self._assign_repo = assignment_repo
        self._session_repo = session_repo
        self._events = event_publisher

    async def lock(
        self,
        db: AsyncSession,
        room_id: UUID,
        expected_version: int,
        actor_id: UUID,
    ) -> SplitSession:
        """
        Lock a room for settlement: compute splits and persist the session.

        1. Validate room is active.
        2. Validate ≥2 participants.
        3. Validate items exist.
        4. If item_wise: validate all items fully claimed.
        5. Transition room → settling (state machine).
        6. Build and persist split session.
        7. Publish event.
        """
        async with db.begin():
            room = await self._room_repo.get_by_id(db, room_id)
            if room is None:
                raise DomainError(code="ROOM_NOT_FOUND", message="Room not found.")

            # Idempotency check: ensure the session does not already exist.
            existing_session = await self._session_repo.get_by_room(db, room_id)
            if existing_session is not None:
                raise RoomAlreadyLocked()

            room_state_machine.validate_transition(room.status, "settling")

            # Claim the room state transition before deriving the lock-time snapshot.
            updated = await self._room_repo.update(
                db, room_id, expected_version, {"status": "settling"}
            )
            if not updated:
                raise VersionConflict()

            participants = await self._participant_repo.list_active(db, room_id)
            if len(participants) < 2:
                raise InsufficientParticipants()

            receipt = await self._receipt_repo.get_by_room(db, room_id)
            if receipt is None:
                raise DomainError(code="NO_RECEIPT", message="No receipt found.")

            items = await self._item_repo.list_by_receipt(db, receipt.id)
            if not items:
                raise NoItems()

            adjustments = await self._adj_repo.list_by_room(db, room_id)
            assignments = await self._assign_repo.list_by_room(db, room_id)

            split_input = SplitSessionBuilder.build_split_input(
                mode=room.split_mode,
                items=items,
                participants=participants,
                adjustments=adjustments,
                assignments=assignments,
            )
            result = SplitCalculator.calculate(split_input)
            snapshot = SplitSessionBuilder.snapshot_adjustments(adjustments)

            # Persist session and totals
            session = await SplitSessionBuilder.persist_session(
                db, self._session_repo, room, result, snapshot,
            )

            seq = await self._events.append_in_tx(
                db, room_id, "split.locked", actor_id,
                {
                    "session_id": str(session.id),
                    "grand_total_paise": result.grand_total_paise,
                },
            )

        await self._events.broadcast(
            room_id, "split.locked",
            {"session_id": str(session.id), "grand_total_paise": result.grand_total_paise},
            seq,
        )
        return session

    async def unlock(
        self,
        db: AsyncSession,
        room_id: UUID,
        expected_version: int,
        actor_id: UUID,
    ) -> None:
        """
        Unlock a room: delete session + totals, transition back to active.
        Claims are preserved.

        1. Validate room is settling.
        2. Delete split_session (cascade deletes participant_totals).
        3. Transition room → active.
        4. Publish event.
        """
        room = await self._room_repo.get_by_id(db, room_id)
        if room is None:
            raise DomainError(code="ROOM_NOT_FOUND", message="Room not found.")

        room_state_machine.validate_transition(room.status, "active")

        async with db.begin():
            # Delete session (cascade removes participant_totals)
            await self._session_repo.delete_by_room(db, room_id)

            # Transition room state back to active
            updated = await self._room_repo.update(
                db, room_id, expected_version, {"status": "active"}
            )
            if not updated:
                raise VersionConflict()

            seq = await self._events.append_in_tx(
                db, room_id, "split.unlocked", actor_id, {},
            )

        await self._events.broadcast(room_id, "split.unlocked", {}, seq)


# ── Convenience facade ───────────────────────────────────────────────────────


class SplitService:
    """
    Convenience wrapper exposing all split operations.
    Delegates to the decomposed coordinators.
    """

    def __init__(
        self,
        lock_coordinator: SplitLockCoordinator,
        preview: SplitPreviewService,
    ) -> None:
        self.lock_coordinator = lock_coordinator
        self.preview = preview

    async def lock(
        self, db: AsyncSession, room_id: UUID, version: int, actor_id: UUID
    ) -> SplitSession:
        return await self.lock_coordinator.lock(db, room_id, version, actor_id)

    async def unlock(
        self, db: AsyncSession, room_id: UUID, version: int, actor_id: UUID
    ) -> None:
        return await self.lock_coordinator.unlock(db, room_id, version, actor_id)

    async def get_current_session(
        self, db: AsyncSession, room_id: UUID
    ) -> SplitSession | None:
        return await self.preview.get_current_session(db, room_id)
