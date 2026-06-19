from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import hash_token
from app.models.line_item import LineItem
from app.models.participant_total import ParticipantTotal
from app.models.receipt import Receipt
from app.models.room import Room
from app.models.room_participant import RoomParticipant
from app.models.split_adjustment import SplitAdjustment
from app.models.split_session import SplitSession
from app.services.registry import (
    get_item_service,
    get_participant_service,
    get_room_service,
    get_split_service,
)
from app.services.split_service import SplitLockCoordinator, SplitSessionBuilder
from app.shared.errors import InvalidStateTransition, RoomAlreadyLocked
from app.split.calculator import SplitCalculator

pytestmark = pytest.mark.asyncio


class _RecordingTx:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        self._db.in_lock_tx = True
        self._db.record("tx.begin")
        return self._db

    async def __aexit__(self, exc_type, exc, tb):
        self._db.record("tx.end")
        self._db.in_lock_tx = False


class _RecordingDb:
    def __init__(self):
        self.in_lock_tx = False
        self.operations = []

    def record(self, operation: str) -> None:
        self.operations.append((operation, self.in_lock_tx))

    def begin(self):
        return _RecordingTx(self)

    def add(self, model) -> None:
        self.record(f"db.add:{type(model).__name__}")

    async def flush(self) -> None:
        self.record("db.flush")


class _TxAwareRoomRepo:
    def __init__(self, room: Room):
        self._room = room

    async def get_by_id(self, db, room_id):
        db.record("room.get_by_id")
        return self._room if room_id == self._room.id else None

    async def update(self, db, room_id, expected_version, update_fields):
        db.record("room.update")
        if room_id != self._room.id or expected_version != self._room.version:
            return False
        for key, value in update_fields.items():
            setattr(self._room, key, value)
        self._room.version += 1
        return True


class _TxAwareReceiptRepo:
    def __init__(self, receipt: Receipt):
        self._receipt = receipt

    async def get_by_room(self, db, room_id):
        db.record("receipt.get_by_room")
        return self._receipt if room_id == self._receipt.room_id else None


class _TxAwareParticipantRepo:
    def __init__(self, participants: list[RoomParticipant]):
        self._participants = participants

    async def list_active(self, db, room_id):
        db.record("participants.list_active")
        return [p for p in self._participants if p.room_id == room_id]


class _TxAwareItemRepo:
    def __init__(self, items: list[LineItem]):
        self._items = items

    async def list_by_receipt(self, db, receipt_id):
        db.record("items.list_by_receipt")
        return [item for item in self._items if item.receipt_id == receipt_id]


class _TxAwareAdjustmentRepo:
    def __init__(self, adjustments: list[SplitAdjustment]):
        self._adjustments = adjustments

    async def list_by_room(self, db, room_id):
        db.record("adjustments.list_by_room")
        return [adj for adj in self._adjustments if adj.room_id == room_id]


class _TxAwareAssignmentRepo:
    async def list_by_room(self, db, room_id):
        db.record("assignments.list_by_room")
        return []


class _TxAwareSessionRepo:
    async def get_by_room(self, db, room_id):
        db.record("session.get_by_room")
        return None

    async def create(self, db, session):
        db.record("session.create")
        session.id = uuid4()
        db.add(session)
        return session


class _TxAwareEvents:
    async def append_in_tx(self, db, room_id, event_type, actor_id, payload):
        db.record("events.append_in_tx")
        return 1

    async def broadcast(self, room_id, event_type, payload, sequence_no):
        return None


async def test_lock_uses_transactional_snapshot(monkeypatch):
    db = _RecordingDb()
    room_id = uuid4()
    receipt_id = uuid4()
    payer_id = uuid4()
    participant_id = uuid4()
    item_id = uuid4()
    adjustment_id = uuid4()

    room = Room(
        id=room_id,
        status="active",
        split_mode="equal",
        version=3,
        expires_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    receipt = Receipt(id=receipt_id, room_id=room_id, source="manual", is_replaceable=True)
    participants = [
        RoomParticipant(
            id=payer_id,
            room_id=room_id,
            nickname="Creator",
            color="#4F46E5",
            role="creator",
            token_hash="payer-token",
        ),
        RoomParticipant(
            id=participant_id,
            room_id=room_id,
            nickname="Bob",
            color="#000000",
            role="participant",
            token_hash="participant-token",
        ),
    ]
    items = [
        LineItem(
            id=item_id,
            receipt_id=receipt_id,
            name="Burger",
            quantity=1,
            total_paise=1000,
            sort_order=0,
        )
    ]
    adjustments = [
        SplitAdjustment(
            id=adjustment_id,
            room_id=room_id,
            type="tax",
            label="Tax",
            amount_paise=100,
            allocation_method="equal",
            sort_order=0,
        )
    ]

    original_build_split_input = SplitSessionBuilder.build_split_input
    original_snapshot_adjustments = SplitSessionBuilder.snapshot_adjustments
    original_calculate = SplitCalculator.calculate

    def build_split_input_in_tx(*args, **kwargs):
        db.record("builder.build_split_input")
        return original_build_split_input(*args, **kwargs)

    def snapshot_adjustments_in_tx(*args, **kwargs):
        db.record("builder.snapshot_adjustments")
        return original_snapshot_adjustments(*args, **kwargs)

    def calculate_in_tx(*args, **kwargs):
        db.record("calculator.calculate")
        return original_calculate(*args, **kwargs)

    monkeypatch.setattr(
        SplitSessionBuilder,
        "build_split_input",
        staticmethod(build_split_input_in_tx),
    )
    monkeypatch.setattr(
        SplitSessionBuilder,
        "snapshot_adjustments",
        staticmethod(snapshot_adjustments_in_tx),
    )
    monkeypatch.setattr(SplitCalculator, "calculate", staticmethod(calculate_in_tx))

    coordinator = SplitLockCoordinator(
        room_repo=_TxAwareRoomRepo(room),
        receipt_repo=_TxAwareReceiptRepo(receipt),
        item_repo=_TxAwareItemRepo(items),
        participant_repo=_TxAwareParticipantRepo(participants),
        adjustment_repo=_TxAwareAdjustmentRepo(adjustments),
        assignment_repo=_TxAwareAssignmentRepo(),
        session_repo=_TxAwareSessionRepo(),
        event_publisher=_TxAwareEvents(),
    )

    await coordinator.lock(
        db,
        room_id=room_id,
        expected_version=room.version,
        actor_id=payer_id,
    )

    required_tx_operations = {
        "room.get_by_id",
        "session.get_by_room",
        "participants.list_active",
        "receipt.get_by_room",
        "items.list_by_receipt",
        "adjustments.list_by_room",
        "assignments.list_by_room",
        "builder.build_split_input",
        "calculator.calculate",
        "builder.snapshot_adjustments",
        "room.update",
        "session.create",
        "db.add:SplitSession",
        "db.add:ParticipantTotal",
        "events.append_in_tx",
    }
    outside_tx = [
        operation
        for operation, in_tx in db.operations
        if operation in required_tx_operations and not in_tx
    ]

    assert outside_tx == []


async def test_lock_creates_session_and_totals(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()
    split_svc = get_split_service()

    room, _, i_token = await room_svc.create_room(db_session, split_mode="equal")
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant1, _ = await part_svc.join_room(db_session, room.id, hash_token(i_token), "Alice", "#FFF")

    # Join a second participant
    _participant2, _ = await part_svc.join_room(
        db_session, room.id, hash_token(i_token), "Bob", "#000"
    )

    # Add item
    await item_svc.add_item(
        db_session, receipt.id, room.id, participant1.id, "Burger", quantity=1, total_paise=1000
    )

    # Reload room to get latest version
    room = await room_svc.get_room(db_session, room.id)

    # Lock
    session = await split_svc.lock(
        db_session,
        room_id=room.id,
        version=room.version,
        actor_id=participant1.id,
    )

    assert session.id is not None
    assert session.grand_total_paise == 1000

    # Check totals
    totals = (await db_session.execute(select(ParticipantTotal).where(ParticipantTotal.split_session_id == session.id))).scalars().all()
    await db_session.commit()
    assert len(totals) == 2

    # Verify idempotency
    with pytest.raises(RoomAlreadyLocked):
        await split_svc.lock(
            db_session,
            room_id=room.id,
            version=room.version,  # The version actually bumped but the idempotency check runs first
            actor_id=participant1.id,
        )


async def test_unlock_removes_session_and_requires_settling_state(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()
    split_svc = get_split_service()

    room, _, i_token = await room_svc.create_room(db_session, split_mode="equal")
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant1, _ = await part_svc.join_room(db_session, room.id, hash_token(i_token), "Alice", "#FFF")
    await part_svc.join_room(db_session, room.id, hash_token(i_token), "Bob", "#000")
    await item_svc.add_item(db_session, receipt.id, room.id, participant1.id, "Burger", quantity=1, total_paise=1000)

    room = await room_svc.get_room(db_session, room.id)

    # Cannot unlock an active room
    with pytest.raises(InvalidStateTransition):
        await split_svc.unlock(
            db_session,
            room_id=room.id,
            version=room.version,
            actor_id=participant1.id,
        )

    # Lock it
    await split_svc.lock(db_session, room.id, room.version, participant1.id)
    room = await room_svc.get_room(db_session, room.id)

    # Unlock it
    await split_svc.unlock(db_session, room.id, room.version, participant1.id)

    # Verify session is deleted
    sessions = (await db_session.execute(select(SplitSession).where(SplitSession.room_id == room.id))).scalars().all()
    await db_session.commit()
    assert len(sessions) == 0

    # Verify room is active again
    room = await room_svc.get_room(db_session, room.id)
    assert room.status == "active"
