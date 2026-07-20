from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func

from app.models.user import User
from app.repositories.interfaces.user import UserRepository
from app.repositories.postgres.base import PostgresRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class PostgresUserRepository(PostgresRepository[User], UserRepository):
    def __init__(self) -> None:
        super().__init__(User)

    async def create(self, db: AsyncSession, user: User) -> User:
        db.add(user)
        await db.flush()
        return user

    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        return await self.fetch_optional(db, user_id)

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        stmt = select(User).where(func.lower(User.username) == username.lower())
        result = await db.execute(stmt)
        return result.scalars().first()

    async def find_by_provider_subject(
        self, db: AsyncSession, provider: str, subject: str
    ) -> User | None:
        stmt = select(User).where(User.provider == provider, User.subject == subject)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def upsert_by_provider_subject(
        self, db: AsyncSession, provider: str, subject: str, email: str | None
    ) -> User:
        stmt = (
            insert(User)
            .values(provider=provider, subject=subject, email=email)
            .on_conflict_do_update(
                index_elements=[User.provider, User.subject],
                set_={"email": email, "updated_at": func.now()},
            )
            .returning(User)
            .execution_options(populate_existing=True)
        )
        result = await db.execute(stmt)
        return result.scalar_one()
