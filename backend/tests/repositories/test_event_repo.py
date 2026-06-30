"""
Tests for PostgresEventRepository — list_after, get_latest_sequence, scoping.

Requires: postgres_container (from conftest.py), db_session, async_engine.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.interfaces.event import AppendResult
from app.repositories.postgres.event import PostgresEventRepository

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def event_repo() -> PostgresEventRepository:
    return PostgresEventRepository()


@pytest_asyncio.fixture
async def seeded_room(db_session: AsyncSession) -> dict:
    """
    Create a minimal room + room_sequence row using raw SQL
    (no service layer needed for repo-level tests).
    Returns {"room_id": UUID, "repo": repo}.
    """
    from sqlalchemy import text

    room_id = uuid4()
    # Insert minimal room row.
    await db_session.execute(
        text("""
            INSERT INTO rooms (id, status, split_mode, expires_at)
            VALUES (:id, 'draft', 'equal', NOW() + INTERVAL '30 days')
        """),
        {"id": str(room_id)},
    )
    # Insert the room_sequence counter (required by append_in_tx).
    await db_session.execute(
        text("INSERT INTO room_sequences (room_id, next_seq) VALUES (:room_id, 0)"),
        {"room_id": str(room_id)},
    )
    await db_session.flush()
    return {"room_id": room_id}


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_append_in_tx_returns_append_result(
    seeded_room: dict,
    db_session: AsyncSession,
    event_repo: PostgresEventRepository,
) -> None:
    """append_in_tx returns an AppendResult with seq, event_id, created_at."""
    room_id = seeded_room["room_id"]
    result = await event_repo.append_in_tx(db_session, room_id, "room.created", None, {})
    assert isinstance(result, AppendResult)
    assert result.sequence_no == 1
    assert result.event_id  # non-empty string UUID
    assert result.created_at is not None


@pytest.mark.asyncio
async def test_list_events_after_sequence(
    seeded_room: dict,
    db_session: AsyncSession,
    event_repo: PostgresEventRepository,
) -> None:
    """list_after returns only events with sequence_no > after_sequence."""
    room_id = seeded_room["room_id"]
    for event_type in ["room.created", "item.created", "item.updated"]:
        await event_repo.append_in_tx(db_session, room_id, event_type, None, {})

    # after_sequence=0 → all 3 events
    all_events = await event_repo.list_after(db_session, room_id, after_sequence=0, limit=100)
    assert len(all_events) == 3

    # after_sequence=1 → events 2 and 3
    after_first = await event_repo.list_after(db_session, room_id, after_sequence=1, limit=100)
    assert len(after_first) == 2
    assert after_first[0].sequence_no == 2

    # after_sequence=3 → nothing
    none_after = await event_repo.list_after(db_session, room_id, after_sequence=3, limit=100)
    assert none_after == []


@pytest.mark.asyncio
async def test_events_ordered_by_sequence(
    seeded_room: dict,
    db_session: AsyncSession,
    event_repo: PostgresEventRepository,
) -> None:
    """list_after always returns events sorted by sequence_no ascending."""
    room_id = seeded_room["room_id"]
    for _ in range(5):
        await event_repo.append_in_tx(db_session, room_id, "item.created", None, {})

    events = await event_repo.list_after(db_session, room_id, after_sequence=0, limit=100)
    seqs = [e.sequence_no for e in events]
    assert seqs == sorted(seqs)
    assert seqs == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_latest_sequence(
    seeded_room: dict,
    db_session: AsyncSession,
    event_repo: PostgresEventRepository,
) -> None:
    """get_latest_sequence returns 0 for a room with no events, then tracks correctly."""
    room_id = seeded_room["room_id"]

    # No events yet → 0
    assert await event_repo.get_latest_sequence(db_session, room_id) == 0

    await event_repo.append_in_tx(db_session, room_id, "room.created", None, {})
    assert await event_repo.get_latest_sequence(db_session, room_id) == 1

    await event_repo.append_in_tx(db_session, room_id, "item.created", None, {})
    assert await event_repo.get_latest_sequence(db_session, room_id) == 2


@pytest.mark.asyncio
async def test_events_scoped_to_room(
    db_session: AsyncSession,
    event_repo: PostgresEventRepository,
) -> None:
    """Events from room A are not returned when querying room B."""
    from sqlalchemy import text

    # Create two rooms.
    room_a = uuid4()
    room_b = uuid4()
    for room_id in (room_a, room_b):
        await db_session.execute(
            text("""
                INSERT INTO rooms (id, status, split_mode, expires_at)
                VALUES (:id, 'draft', 'equal', NOW() + INTERVAL '30 days')
            """),
            {"id": str(room_id)},
        )
        await db_session.execute(
            text("INSERT INTO room_sequences (room_id, next_seq) VALUES (:room_id, 0)"),
            {"room_id": str(room_id)},
        )
    await db_session.flush()

    # Room A gets 3 events, room B gets 1.
    for _ in range(3):
        await event_repo.append_in_tx(db_session, room_a, "item.created", None, {})
    await event_repo.append_in_tx(db_session, room_b, "room.created", None, {})

    events_a = await event_repo.list_after(db_session, room_a, after_sequence=0, limit=100)
    events_b = await event_repo.list_after(db_session, room_b, after_sequence=0, limit=100)

    assert len(events_a) == 3
    assert len(events_b) == 1
    # Sequence numbers are independent per room.
    assert all(e.room_id == room_a for e in events_a)
    assert events_b[0].room_id == room_b


@pytest.mark.asyncio
async def test_list_after_respects_limit(
    seeded_room: dict,
    db_session: AsyncSession,
    event_repo: PostgresEventRepository,
) -> None:
    """list_after respects the limit parameter."""
    room_id = seeded_room["room_id"]
    for _ in range(10):
        await event_repo.append_in_tx(db_session, room_id, "item.created", None, {})

    events = await event_repo.list_after(db_session, room_id, after_sequence=0, limit=3)
    assert len(events) == 3
    assert [e.sequence_no for e in events] == [1, 2, 3]
