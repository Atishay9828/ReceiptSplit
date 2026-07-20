"""Tests for PostgresEventRepository — Atomic sequencing and rollback."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models.room import Room
from app.models.room_event import RoomEvent
from app.repositories.postgres.event import PostgresEventRepository
from app.repositories.postgres.room import PostgresRoomRepository


async def _create_room_direct(engine: AsyncEngine) -> str:
    """Create a room directly using the engine, committed to the real DB.

    Concurrent tests need rows visible across independent connections,
    so we commit outside any test-scoped SAVEPOINT.
    """
    from sqlalchemy.ext.asyncio import AsyncSession as AS

    async with engine.connect() as conn, conn.begin():
        session = AS(bind=conn, expire_on_commit=False)
        repo = PostgresRoomRepository()
        room = Room(
            status="draft",
            split_mode="equal",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        await repo.create(session, room)
        await session.flush()
        room_id = str(room.id)
        await session.close()
    return room_id


@pytest.mark.asyncio
async def test_concurrent_event_sequencing(async_engine: AsyncEngine):
    """Verifies TXN-2 / DB-1: Atomic Event Sequencing under concurrency.

    10 workers each append one event concurrently.
    The resulting sequence numbers must be a gapless 1..10.
    """
    from uuid import UUID

    room_id_str = await _create_room_direct(async_engine)
    room_id = UUID(room_id_str)
    event_repo = PostgresEventRepository()

    async def append_event(worker_id: int) -> int:
        async with async_engine.connect() as conn, conn.begin():
            session = AsyncSession(bind=conn, expire_on_commit=False)
            seq = await event_repo.append_in_tx(
                session,
                room_id=room_id,
                event_type="test.event",
                actor_id=None,
                payload={"worker": worker_id},
            )
            await session.close()
            return seq

    count = 10
    tasks = [append_event(i) for i in range(count)]

    # Gather results.
    results = await asyncio.gather(*tasks)

    # All sequence numbers should be unique, continuous from 1 to 50.
    sequences = sorted([r.sequence_no for r in results])
    assert sequences == list(range(1, count + 1)), f"Expected gapless 1..10, got {sequences}"


@pytest.mark.asyncio
async def test_event_rollback_on_transaction_failure(async_engine: AsyncEngine):
    """Verifies that a failed transaction rolls back BOTH the sequence increment AND the event insert.

    1. Start a transaction, append an event, then raise → rollback.
    2. Append a successful event in a new transaction.
    3. Assert the successful event got sequence_no = 1 (not 2).
    """
    from uuid import UUID

    room_id_str = await _create_room_direct(async_engine)
    room_id = UUID(room_id_str)
    event_repo = PostgresEventRepository()

    # Transaction 1: append + deliberate failure → full rollback
    try:
        async with async_engine.connect() as conn, conn.begin():
            session = AsyncSession(bind=conn, expire_on_commit=False)
            await event_repo.append_in_tx(
                session,
                room_id=room_id,
                event_type="failed_event",
                actor_id=None,
                payload={},
            )
            await session.close()
            raise ValueError("Simulated business logic failure")
    except ValueError:
        pass  # Expected

    # Transaction 2: successful append
    async with async_engine.connect() as conn, conn.begin():
        session = AsyncSession(bind=conn, expire_on_commit=False)
        seq = await event_repo.append_in_tx(
            session,
            room_id=room_id,
            event_type="successful_event",
            actor_id=None,
            payload={},
        )
        await session.close()

    assert seq.sequence_no == 1, f"Expected seq=1 after rollback, got {seq.sequence_no}"

    # Insert a second event and commit successfully.
    async with async_engine.connect() as conn:
        result = await conn.execute(select(RoomEvent).where(RoomEvent.room_id == room_id))
        events = result.all()
        assert len(events) == 1
        assert events[0].event_type == "successful_event"
        assert events[0].sequence_no == 1
