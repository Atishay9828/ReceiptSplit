"""Tests for PostgresRoomRepository — CRUD and CAS operations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from app.models.room import Room
from app.repositories.postgres.room import PostgresRoomRepository
from app.shared.errors import DomainError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _make_room() -> Room:
    return Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


@pytest.mark.asyncio
async def test_room_create_and_read(db_session: AsyncSession):
    repo = PostgresRoomRepository()
    room = _make_room()

    await repo.create(db_session, room)
    await db_session.flush()

    assert room.id is not None

    fetched = await repo.get_by_id(db_session, room.id)
    assert fetched is not None
    assert fetched.status == "draft"
    assert fetched.version == 1


@pytest.mark.asyncio
async def test_room_cas_update_success(db_session: AsyncSession):
    repo = PostgresRoomRepository()
    room = _make_room()

    await repo.create(db_session, room)
    await db_session.flush()
    room_id = room.id  # capture before expire

    updated = await repo.update(db_session, room_id, 1, {"payer_name": "Alice"})
    assert updated is True

    # Expire cached state so the next read hits the DB
    await db_session.flush()
    db_session.expire_all()

    fetched = await repo.get_by_id(db_session, room_id)
    assert fetched is not None
    assert fetched.payer_name == "Alice"
    assert fetched.version == 2


@pytest.mark.asyncio
async def test_room_cas_update_version_mismatch(db_session: AsyncSession):
    repo = PostgresRoomRepository()
    room = _make_room()

    await repo.create(db_session, room)
    await db_session.flush()

    # Version is 1, but pass stale version 999
    updated = await repo.update(db_session, room.id, 999, {"payer_name": "Bob"})
    assert updated is False


@pytest.mark.asyncio
async def test_room_fetch_one_not_found(db_session: AsyncSession):
    repo = PostgresRoomRepository()
    with pytest.raises(DomainError) as exc:
        await repo.fetch_one(db_session, uuid4())
    assert "ROOM_NOT_FOUND" in exc.value.code


@pytest.mark.asyncio
async def test_room_archive(db_session: AsyncSession):
    repo = PostgresRoomRepository()
    room = _make_room()

    await repo.create(db_session, room)
    await db_session.flush()
    room_id = room.id  # capture before expire

    result = await repo.archive(db_session, room_id, 1)
    assert result is True

    await db_session.flush()
    db_session.expire_all()

    fetched = await repo.get_by_id(db_session, room_id)
    assert fetched is not None
    assert fetched.status == "archived"
    assert fetched.version == 2


@pytest.mark.asyncio
async def test_room_expire(db_session: AsyncSession):
    repo = PostgresRoomRepository()
    room = _make_room()

    await repo.create(db_session, room)
    await db_session.flush()
    room_id = room.id  # capture before expire

    result = await repo.expire(db_session, room_id, 1)
    assert result is True

    await db_session.flush()
    db_session.expire_all()

    fetched = await repo.get_by_id(db_session, room_id)
    assert fetched is not None
    assert fetched.status == "expired"
    assert fetched.version == 2
