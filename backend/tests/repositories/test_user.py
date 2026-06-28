from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.models.user import User
from app.repositories.postgres.user import PostgresUserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_user_create_and_find_by_provider_subject(db_session: AsyncSession):
    repo = PostgresUserRepository()
    user = User(provider="google", subject="oidc-sub-1", email="aj@example.com")

    created = await repo.create(db_session, user)
    await db_session.flush()

    fetched = await repo.find_by_provider_subject(db_session, "google", "oidc-sub-1")

    assert created.id is not None
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == "aj@example.com"


@pytest.mark.asyncio
async def test_user_upsert_creates_then_updates_existing_provider_subject(
    db_session: AsyncSession,
):
    repo = PostgresUserRepository()

    first = await repo.upsert_by_provider_subject(
        db_session,
        provider="google",
        subject="oidc-sub-1",
        email="old@example.com",
    )
    await db_session.flush()
    first_id = first.id

    second = await repo.upsert_by_provider_subject(
        db_session,
        provider="google",
        subject="oidc-sub-1",
        email="new@example.com",
    )
    await db_session.flush()

    assert second.id == first_id
    assert second.email == "new@example.com"


@pytest.mark.asyncio
async def test_user_upsert_keeps_nullable_email(db_session: AsyncSession):
    repo = PostgresUserRepository()

    user = await repo.upsert_by_provider_subject(
        db_session,
        provider="google",
        subject="oidc-sub-2",
        email=None,
    )
    await db_session.flush()

    assert user.id is not None
    assert user.email is None
