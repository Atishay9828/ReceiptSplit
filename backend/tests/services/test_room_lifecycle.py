import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt
from app.models.room_invite import RoomInvite
from app.models.room_participant import RoomParticipant
from app.services.registry import get_room_service
from app.shared.errors import InvalidStateTransition

pytestmark = pytest.mark.asyncio


async def test_room_creation_creates_all_records(db_session: AsyncSession):
    svc = get_room_service()
    room, _c_token, _i_token = await svc.create_room(db_session, split_mode="equal")

    assert room.id is not None
    assert room.status == "draft"

    # Check receipt
    receipts = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().all()
    await db_session.commit()
    assert len(receipts) == 1

    # Check invite
    invites = (await db_session.execute(select(RoomInvite).where(RoomInvite.room_id == room.id))).scalars().all()
    await db_session.commit()
    assert len(invites) == 1

    # Check participant
    participants = (await db_session.execute(select(RoomParticipant).where(RoomParticipant.room_id == room.id))).scalars().all()
    await db_session.commit()
    assert len(participants) == 1
    assert participants[0].role == "creator"


async def test_room_creation_creates_creator_participant(db_session: AsyncSession):
    svc = get_room_service()
    room, _c_token, _i_token = await svc.create_room(db_session)

    # Participant assertions
    participants = (await db_session.execute(select(RoomParticipant).where(RoomParticipant.room_id == room.id))).scalars().all()
    await db_session.commit()
    assert len(participants) == 1
    assert participants[0].role == "creator"
    assert participants[0].nickname == "Creator"


async def test_invalid_state_transition(db_session: AsyncSession):
    svc = get_room_service()
    room, _, _ = await svc.create_room(db_session)

    participants = (await db_session.execute(select(RoomParticipant).where(RoomParticipant.room_id == room.id))).scalars().all()
    await db_session.commit()

    # Draft -> Settling is invalid
    with pytest.raises(InvalidStateTransition):
        await svc.transition_room(
            db_session,
            room_id=room.id,
            expected_version=room.version,
            to_state="settling",
            actor_id=participants[0].id,
        )
