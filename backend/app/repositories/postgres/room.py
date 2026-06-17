from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.models.room import Room
from app.models.room_sequence import RoomSequence
from app.repositories.interfaces.room import RoomRepository
from app.repositories.postgres.base import PostgresRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class PostgresRoomRepository(PostgresRepository[Room], RoomRepository):
    def __init__(self) -> None:
        super().__init__(Room)

    async def create(self, db: AsyncSession, room: Room) -> Room:
        db.add(room)
        # Create corresponding room sequence (TXN-1)
        seq = RoomSequence(room_id=room.id, next_seq=0)
        db.add(seq)
        return room

    async def get_by_id(self, db: AsyncSession, room_id: UUID) -> Room | None:
        return await self.fetch_optional(db, room_id)

    async def update(
        self, db: AsyncSession, room_id: UUID, expected_version: int, update_fields: dict[str, Any]
    ) -> bool:
        return await self.cas_update(
            db,
            table="rooms",
            pk_column="id",
            pk_value=room_id,
            expected_version=expected_version,
            update_fields=update_fields,
            has_updated_at=True,
        )

    async def archive(self, db: AsyncSession, room_id: UUID, expected_version: int) -> bool:
        return await self.cas_update(
            db,
            table="rooms",
            pk_column="id",
            pk_value=room_id,
            expected_version=expected_version,
            update_fields={"status": "archived"},
            has_updated_at=True,
        )

    async def expire(self, db: AsyncSession, room_id: UUID, expected_version: int) -> bool:
        return await self.cas_update(
            db,
            table="rooms",
            pk_column="id",
            pk_value=room_id,
            expected_version=expected_version,
            update_fields={"status": "expired"},
            has_updated_at=True,
        )
