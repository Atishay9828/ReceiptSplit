from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.split_adjustment import SplitAdjustment


class AdjustmentRepository(Protocol):
    async def create(self, db: AsyncSession, adjustment: SplitAdjustment) -> SplitAdjustment:
        """Persists a new split adjustment."""
        ...

    async def list_by_room(self, db: AsyncSession, room_id: UUID) -> list[SplitAdjustment]:
        """Lists active adjustments for a room (where deleted_at IS NULL)."""
        ...

    async def soft_delete(
        self, db: AsyncSession, adjustment_id: UUID, expected_version: int
    ) -> bool:
        """Soft-deletes a split adjustment using CAS."""
        ...
