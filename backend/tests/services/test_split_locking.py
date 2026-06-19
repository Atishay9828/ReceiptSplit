import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import hash_token
from app.models.participant_total import ParticipantTotal
from app.models.receipt import Receipt
from app.models.room import Room
from app.models.split_session import SplitSession
from app.services.registry import (
    get_item_service,
    get_participant_service,
    get_room_service,
    get_split_service,
)
from app.shared.errors import DomainError, InvalidStateTransition, RoomAlreadyLocked

pytestmark = pytest.mark.asyncio


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
    participant2, _ = await part_svc.join_room(
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
    session = await split_svc.lock(db_session, room.id, room.version, participant1.id)
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
