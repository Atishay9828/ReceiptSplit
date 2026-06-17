import asyncio

import pytest

import app.config
from app.models.room import Room
from app.models.room_invite import RoomInvite
from app.repositories.postgres.participant import PostgresParticipantRepository
from app.repositories.postgres.room import PostgresRoomRepository
from app.shared.errors import DomainError


@pytest.mark.asyncio
async def test_participant_join_concurrency_and_limit(db_session, async_engine, monkeypatch):
    """Verifies TXN-3: Advisory Lock for Room Joins."""
    repo = PostgresRoomRepository()
    room = Room(status="draft", split_mode="equal")
    await repo.create(db_session, room)
    
    invite = RoomInvite(room_id=room.id, token_hash="test_invite", type="participant")
    db_session.add(invite)
    await db_session.commit()
    
    room_id = room.id
    participant_repo = PostgresParticipantRepository()
    
    # Override settings for this test
    monkeypatch.setattr(app.config.settings, "max_participants_per_room", 3)
    
    async def join_worker(worker_id):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        async_session = async_sessionmaker(async_engine, expire_on_commit=False, autoflush=False)
        async with async_session() as session:
            try:
                async with session.begin():
                    await participant_repo.join_room_in_tx(
                        session,
                        room_id=room_id,
                        invite_token_hash="test_invite",
                        nickname=f"Worker {worker_id}",
                        color="#000000",
                        new_token_hash=f"token_{worker_id}"
                    )
                    return True
            except DomainError as e:
                if e.code == "ROOM_FULL":
                    return False
                raise

    # Spawn 5 concurrent joins
    tasks = [join_worker(i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    
    successes = sum(1 for r in results if r is True)
    failures = sum(1 for r in results if r is False)
    
    # Exactly 3 should succeed and 2 should fail with ROOM_FULL
    assert successes == 3
    assert failures == 2
