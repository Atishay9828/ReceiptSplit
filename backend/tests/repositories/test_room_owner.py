from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from app.models.room import Room
from app.models.user import User
from app.repositories.postgres.room import PostgresRoomRepository
from app.repositories.postgres.user import PostgresUserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _make_room() -> Room:
    return Room(
        status="draft",
        split_mode="equal",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


async def _create_user(
    db_session: AsyncSession,
    provider: str = "google",
    subject: str = "oidc-sub-1",
) -> User:
    repo = PostgresUserRepository()
    user = User(provider=provider, subject=subject, email=f"{subject}@example.com")
    await repo.create(db_session, user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_attach_room_to_user(db_session: AsyncSession) -> None:
    room_repo = PostgresRoomRepository()
    user = await _create_user(db_session)
    room = await room_repo.create(db_session, _make_room())
    await db_session.flush()
    room_id = room.id
    user_id = user.id

    attached = await room_repo.attach_creator(db_session, room_id, user_id)
    await db_session.flush()
    db_session.expire_all()

    fetched = await room_repo.get_by_id(db_session, room_id)

    assert attached is True
    assert fetched is not None
    assert fetched.creator_user_id == user_id


@pytest.mark.asyncio
async def test_list_rooms_by_user_only_returns_owned_rooms(db_session: AsyncSession) -> None:
    room_repo = PostgresRoomRepository()
    owner = await _create_user(db_session, subject="owner")
    unrelated = await _create_user(db_session, subject="unrelated")
    owned = await room_repo.create(db_session, _make_room())
    other = await room_repo.create(db_session, _make_room())
    legacy = await room_repo.create(db_session, _make_room())
    await db_session.flush()
    owner_id = owner.id
    unrelated_id = unrelated.id
    owned_id = owned.id
    other_id = other.id
    legacy_id = legacy.id

    await room_repo.attach_creator(db_session, owned_id, owner_id)
    await room_repo.attach_creator(db_session, other_id, unrelated_id)
    await db_session.flush()
    db_session.expire_all()

    owner_rooms = await room_repo.list_by_creator(db_session, owner_id)
    unrelated_rooms = await room_repo.list_by_creator(db_session, unrelated_id)

    assert [room.id for room in owner_rooms] == [owned_id]
    assert [room.id for room in unrelated_rooms] == [other_id]
    assert legacy_id not in {room.id for room in owner_rooms}


@pytest.mark.asyncio
async def test_existing_room_without_creator_remains_valid(db_session: AsyncSession) -> None:
    room_repo = PostgresRoomRepository()
    room = await room_repo.create(db_session, _make_room())
    await db_session.flush()
    room_id = room.id
    db_session.expire_all()

    fetched = await room_repo.get_by_id(db_session, room_id)

    assert fetched is not None
    assert fetched.creator_user_id is None
