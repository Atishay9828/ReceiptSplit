"""Tests for PostgresParticipantRepository — Advisory lock concurrency control."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import app.config
from app.models.room import Room
from app.models.room_invite import RoomInvite
from app.repositories.postgres.participant import PostgresParticipantRepository
from app.repositories.postgres.room import PostgresRoomRepository
from app.shared.errors import DomainError


async def _create_room_with_invite(engine: AsyncEngine) -> tuple[str, str]:
    """Create a room + invite, committed to the real DB for cross-connection visibility."""
    async with engine.connect() as conn, conn.begin():
        session = AsyncSession(bind=conn, expire_on_commit=False)
        repo = PostgresRoomRepository()
        room = Room(
            status="draft",
            split_mode="equal",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        await repo.create(session, room)
        await session.flush()

        invite = RoomInvite(
            room_id=room.id,
            token_hash="test_invite_concurrent",
            type="participant",
        )
        session.add(invite)
        await session.flush()

        room_id = str(room.id)
        invite_hash = invite.token_hash
        await session.close()

    return room_id, invite_hash


@pytest.mark.asyncio
async def test_concurrent_join_limit(async_engine: AsyncEngine, monkeypatch):
    """Verifies TXN-3: pg_advisory_xact_lock serializes concurrent joins.

    With max_participants_per_room=3 and 5 concurrent join attempts:
    - Exactly 3 should succeed
    - Exactly 2 should get ROOM_FULL
    """
    from uuid import UUID

    # Set limit to 3 for this test
    monkeypatch.setattr(app.config.settings, "max_participants_per_room", 3)

    room_id_str, invite_hash = await _create_room_with_invite(async_engine)
    room_id = UUID(room_id_str)
    participant_repo = PostgresParticipantRepository()

    async def join_worker(worker_id: int) -> bool:
        async with async_engine.connect() as conn, conn.begin():
            session = AsyncSession(bind=conn, expire_on_commit=False)
            try:
                await participant_repo.join_room_in_tx(
                    session,
                    room_id=room_id,
                    invite_token_hash=invite_hash,
                    nickname=f"Worker {worker_id}",
                    color="#000000",
                    new_token_hash=f"concurrent_token_{worker_id}",
                )
                await session.flush()
                await session.close()
                return True
            except DomainError as e:
                await session.close()
                if e.code == "ROOM_FULL":
                    return False
                raise

    tasks = [join_worker(i) for i in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Fail fast on unexpected exceptions
    for res in results:
        if isinstance(res, Exception):
            raise res

    successes = sum(1 for r in results if r is True)
    failures = sum(1 for r in results if r is False)

    assert successes == 3, f"Expected 3 successful joins, got {successes}"
    assert failures == 2, f"Expected 2 ROOM_FULL failures, got {failures}"


@pytest.mark.asyncio
async def test_participant_get_by_token(db_session: AsyncSession):
    """Test retrieving a participant by their token hash."""
    repo = PostgresRoomRepository()
    room = Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await repo.create(db_session, room)
    await db_session.flush()

    # Create invite
    invite = RoomInvite(
        room_id=room.id,
        token_hash="get_by_token_invite",
        type="participant",
    )
    db_session.add(invite)
    await db_session.flush()

    participant_repo = PostgresParticipantRepository()
    await participant_repo.join_room_in_tx(
        db_session,
        room_id=room.id,
        invite_token_hash="get_by_token_invite",
        nickname="TestUser",
        color="#FF0000",
        new_token_hash="unique_participant_token_123",
    )
    await db_session.flush()

    # Retrieve by token
    found = await participant_repo.get_by_token(db_session, "unique_participant_token_123")
    assert found is not None
    assert found.nickname == "TestUser"
    assert found.color == "#FF0000"

    # Not found
    missing = await participant_repo.get_by_token(db_session, "nonexistent_token")
    assert missing is None


@pytest.mark.asyncio
async def test_participant_list_active(db_session: AsyncSession):
    """Test listing active participants for a room."""
    repo = PostgresRoomRepository()
    room = Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await repo.create(db_session, room)
    await db_session.flush()

    invite = RoomInvite(
        room_id=room.id,
        token_hash="list_active_invite",
        type="participant",
    )
    db_session.add(invite)
    await db_session.flush()

    participant_repo = PostgresParticipantRepository()
    await participant_repo.join_room_in_tx(
        db_session,
        room_id=room.id,
        invite_token_hash="list_active_invite",
        nickname="User1",
        color="#00FF00",
        new_token_hash="list_active_token_1",
    )
    await db_session.flush()

    active = await participant_repo.list_active(db_session, room.id)
    assert len(active) == 1
    assert active[0].nickname == "User1"
