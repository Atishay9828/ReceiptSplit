from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.split_session import SplitSession


class SplitSessionRepository(Protocol):
    async def create(self, db: AsyncSession, session: SplitSession) -> SplitSession:
        """Persists a new split session."""
        ...

    async def get_by_room(self, db: AsyncSession, room_id: UUID) -> SplitSession | None:
        """Retrieves the active split session for a room."""
        ...

    async def delete_by_room(self, db: AsyncSession, room_id: UUID) -> bool:
        """Deletes the split session for a room. Returns True if a row was deleted."""
        ...

