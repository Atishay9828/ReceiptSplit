import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room_event import RoomEvent
from app.services.registry import get_participant_service, get_room_service
from app.shared.types import COLOR_PALETTE

pytestmark = pytest.mark.asyncio


async def test_join_publishes_event(db_session: AsyncSession):
    room_svc = get_room_service()
    part_svc = get_participant_service()

    room, _, invite_token = await room_svc.create_room(db_session)

    # Check baseline events (room.created)
    events_before = (await db_session.execute(select(RoomEvent).where(RoomEvent.room_id == room.id))).scalars().all()
    await db_session.commit()
    baseline = len(events_before)

    from app.auth.tokens import hash_token

    _participant, _token = await part_svc.join_room(
        db_session,
        room_id=room.id,
        invite_token_hash=hash_token(invite_token),
        nickname="Alice",
        color=COLOR_PALETTE[1],
    )

    # We need to test if event is published.
    events_after = (await db_session.execute(select(RoomEvent).where(RoomEvent.room_id == room.id))).scalars().all()
    await db_session.commit()
    assert len(events_after) == baseline + 1

    last_event = sorted(events_after, key=lambda e: e.sequence_no)[-1]
    assert last_event.event_type == "participant.joined"
    assert last_event.payload["nickname"] == "Alice"
