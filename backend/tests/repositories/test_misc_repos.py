"""Tests for remaining repositories — Item, Adjustment, SplitSession, Receipt, ReceiptEdit."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.room import Room
from app.models.room_invite import RoomInvite
from app.models.room_participant import RoomParticipant
from app.models.split_adjustment import SplitAdjustment
from app.models.split_session import SplitSession
from app.repositories.postgres.adjustment import PostgresAdjustmentRepository
from app.repositories.postgres.item import PostgresItemRepository
from app.repositories.postgres.receipt import PostgresReceiptRepository
from app.repositories.postgres.receipt_edit import PostgresReceiptEditRepository
from app.repositories.postgres.room import PostgresRoomRepository
from app.repositories.postgres.split_session import PostgresSplitSessionRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def _setup_room_with_receipt(db: AsyncSession) -> tuple[Room, Receipt, RoomParticipant]:
    """Helper: create a room, receipt, invite, and participant."""
    repo = PostgresRoomRepository()
    room = Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await repo.create(db, room)
    await db.flush()

    receipt = Receipt(room_id=room.id, source="manual", is_replaceable=True)
    db.add(receipt)
    await db.flush()

    invite = RoomInvite(room_id=room.id, token_hash="misc_test_invite", type="creator")
    db.add(invite)
    await db.flush()

    participant = RoomParticipant(
        room_id=room.id,
        invite_id=invite.id,
        nickname="Creator",
        color="#AABBCC",
        role="creator",
        token_hash="misc_test_participant_token",
    )
    db.add(participant)
    await db.flush()

    return room, receipt, participant


# ── Item Repository ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_item_create_and_read(db_session: AsyncSession):
    repo = PostgresItemRepository()
    _, receipt, _ = await _setup_room_with_receipt(db_session)

    item = LineItem(
        receipt_id=receipt.id,
        name="Paneer Tikka",
        quantity=2,
        total_paise=45000,
    )
    await repo.create(db_session, item)
    await db_session.flush()

    fetched = await repo.get(db_session, item.id)
    assert fetched is not None
    assert fetched.name == "Paneer Tikka"
    assert fetched.quantity == 2
    assert fetched.total_paise == 45000
    assert fetched.version == 1


@pytest.mark.asyncio
async def test_item_cas_update(db_session: AsyncSession):
    repo = PostgresItemRepository()
    _, receipt, _ = await _setup_room_with_receipt(db_session)

    item = LineItem(receipt_id=receipt.id, name="Dal Makhani", quantity=1, total_paise=30000)
    await repo.create(db_session, item)
    await db_session.flush()

    updated = await repo.update(db_session, item.id, 1, {"name": "Dal Tadka"})
    assert updated is True

    # Version mismatch
    updated = await repo.update(db_session, item.id, 1, {"name": "Naan"})
    assert updated is False


@pytest.mark.asyncio
async def test_item_soft_delete(db_session: AsyncSession):
    repo = PostgresItemRepository()
    _, receipt, _ = await _setup_room_with_receipt(db_session)

    item = LineItem(receipt_id=receipt.id, name="Naan", quantity=3, total_paise=9000)
    await repo.create(db_session, item)
    await db_session.flush()

    deleted = await repo.soft_delete(db_session, item.id, 1)
    assert deleted is True

    # Can't soft-delete again with old version
    deleted = await repo.soft_delete(db_session, item.id, 1)
    assert deleted is False


# ── Adjustment Repository ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adjustment_create_and_list(db_session: AsyncSession):
    repo = PostgresAdjustmentRepository()
    room_repo = PostgresRoomRepository()
    room = Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await room_repo.create(db_session, room)
    await db_session.flush()

    adj = SplitAdjustment(
        room_id=room.id,
        type="tax",
        label="GST 18%",
        amount_paise=5400,
        rate_basis_points=1800,
        allocation_method="proportional",
        sort_order=0,
    )
    await repo.create(db_session, adj)
    await db_session.flush()

    items = await repo.list_by_room(db_session, room.id)
    assert len(items) == 1
    assert items[0].label == "GST 18%"


@pytest.mark.asyncio
async def test_adjustment_soft_delete(db_session: AsyncSession):
    repo = PostgresAdjustmentRepository()
    room_repo = PostgresRoomRepository()
    room = Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await room_repo.create(db_session, room)
    await db_session.flush()

    adj = SplitAdjustment(
        room_id=room.id,
        type="discount",
        label="10% Off",
        amount_paise=-3000,
        allocation_method="equal",
        sort_order=1,
    )
    await repo.create(db_session, adj)
    await db_session.flush()

    deleted = await repo.soft_delete(db_session, adj.id, 1)
    assert deleted is True

    items = await repo.list_by_room(db_session, room.id)
    assert len(items) == 0  # Soft-deleted items excluded


# ── Receipt Repository ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_receipt_create_and_get_by_room(db_session: AsyncSession):
    repo = PostgresReceiptRepository()
    room_repo = PostgresRoomRepository()
    room = Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await room_repo.create(db_session, room)
    await db_session.flush()

    receipt = Receipt(room_id=room.id, source="manual", is_replaceable=True)
    await repo.create(db_session, receipt)
    await db_session.flush()

    fetched = await repo.get_by_room(db_session, room.id)
    assert fetched is not None
    assert fetched.source == "manual"


@pytest.mark.asyncio
async def test_receipt_update_not_implemented(db_session: AsyncSession):
    repo = PostgresReceiptRepository()
    with pytest.raises(NotImplementedError):
        await repo.update(db_session, None, 1, {})


# ── SplitSession Repository ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_split_session_create_and_get(db_session: AsyncSession):
    repo = PostgresSplitSessionRepository()
    room_repo = PostgresRoomRepository()
    room = Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await room_repo.create(db_session, room)
    await db_session.flush()

    session = SplitSession(
        room_id=room.id,
        mode="equal",
        grand_total_paise=100000,
    )
    await repo.create(db_session, session)
    await db_session.flush()

    fetched = await repo.get_by_room(db_session, room.id)
    assert fetched is not None
    assert fetched.mode == "equal"
    assert fetched.grand_total_paise == 100000


# ── ReceiptEdit Repository ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_receipt_edit_append(db_session: AsyncSession):
    repo = PostgresReceiptEditRepository()
    _, receipt, participant = await _setup_room_with_receipt(db_session)

    edit = await repo.append_in_tx(
        db_session,
        receipt_id=receipt.id,
        participant_id=participant.id,
        field="line_item.name",
        old_value="Panner Tikka",
        new_value="Paneer Tikka",
    )

    assert edit is not None
    assert edit.field == "line_item.name"
    assert edit.old_value == "Panner Tikka"
    assert edit.new_value == "Paneer Tikka"
