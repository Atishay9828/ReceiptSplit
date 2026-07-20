from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User


class UserRepository(Protocol):
    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """Finds a user by case-insensitive username."""
        ...

    async def create(self, db: AsyncSession, user: User) -> User:
        """Persists a new user."""
        ...

    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        """Retrieves a user by ID."""
        ...

    async def find_by_provider_subject(
        self, db: AsyncSession, provider: str, subject: str
    ) -> User | None:
        """Finds a user by OIDC provider and subject."""
        ...

    async def upsert_by_provider_subject(
        self, db: AsyncSession, provider: str, subject: str, email: str | None
    ) -> User:
        """Creates or updates a user for an OIDC provider and subject."""
        ...
