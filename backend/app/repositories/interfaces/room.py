from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room


class RoomRepository(Protocol):
    async def create(self, db: AsyncSession, room: Room) -> Room:
        """Persists a new room."""
        ...

    async def get_by_id(self, db: AsyncSession, room_id: UUID) -> Room | None:
        """Retrieves a room by ID."""
        ...

    async def attach_creator(self, db: AsyncSession, room_id: UUID, user_id: UUID) -> bool:
        """Associates a room with its authenticated creator."""
        ...

    async def list_by_creator(self, db: AsyncSession, user_id: UUID) -> list[Room]:
        """Lists rooms created by a user."""
        ...

    async def update(
        self, db: AsyncSession, room_id: UUID, expected_version: int, update_fields: dict[str, Any]
    ) -> bool:
        """Executes a CAS update on a room."""
        ...

    async def archive(self, db: AsyncSession, room_id: UUID, expected_version: int) -> bool:
        """Transitions a room to archived state."""
        ...

    async def expire(self, db: AsyncSession, room_id: UUID, expected_version: int) -> bool:
        """Transitions a room to expired state."""
        ...
