import asyncio

import pytest
from sqlalchemy import select

from app.models.room import Room
from app.models.room_event import RoomEvent
from app.repositories.postgres.event import PostgresEventRepository
from app.repositories.postgres.room import PostgresRoomRepository


@pytest.mark.asyncio
async def test_concurrent_event_sequencing(db_session, async_engine):
    """Verifies TXN-2: Atomic Event Sequencing."""
    # Setup Room
    repo = PostgresRoomRepository()
    room = Room(status="draft", split_mode="equal")
    await repo.create(db_session, room)
    await db_session.commit()
    
    room_id = room.id
    event_repo = PostgresEventRepository()
    
    async def append_event(worker_id):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        async_session = async_sessionmaker(async_engine, expire_on_commit=False, autoflush=False)
        async with async_session() as session:
            async with session.begin():
                seq = await event_repo.append_in_tx(
                    session,
                    room_id=room_id,
                    event_type="test_event",
                    actor_id=None,
                    payload={"worker": worker_id}
                )
                return seq

    # Run 10 concurrent appends
    tasks = [append_event(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    # Sequences must be perfectly 1 to 10
    sequences = sorted(results)
    assert sequences == list(range(1, 11))


@pytest.mark.asyncio
async def test_event_rollback_scenario(db_session):
    """Verifies that failed business logic rolls back both sequence increment and event insertion."""
    repo = PostgresRoomRepository()
    room = Room(status="draft", split_mode="equal")
    await repo.create(db_session, room)
    await db_session.commit()
    
    event_repo = PostgresEventRepository()
    room_id = room.id
    
    # Simulate an event inside a transaction that rolls back
    try:
        async with db_session.begin_nested():
            await event_repo.append_in_tx(
                db_session,
                room_id=room_id,
                event_type="failed_event",
                actor_id=None,
                payload={}
            )
            raise ValueError("Business logic failed!")
    except ValueError:
        pass
        
    # Append a successful event afterwards
    seq = await event_repo.append_in_tx(
        db_session,
        room_id=room_id,
        event_type="successful_event",
        actor_id=None,
        payload={}
    )
    await db_session.commit()
    
    # The sequence should be 1 since the failed one was fully rolled back
    assert seq == 1
    
    events = (await db_session.execute(select(RoomEvent).where(RoomEvent.room_id == room_id))).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "successful_event"
    assert events[0].sequence_no == 1
