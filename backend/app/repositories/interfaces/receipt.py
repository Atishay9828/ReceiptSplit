from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt


class ReceiptRepository(Protocol):
    async def create(self, db: AsyncSession, receipt: Receipt) -> Receipt:
        """Persists a new receipt."""
        ...

    async def get_by_room(self, db: AsyncSession, room_id: UUID) -> Receipt | None:
        """Retrieves the single receipt associated with a room."""
        ...

    async def update(
        self, db: AsyncSession, receipt_id: UUID, expected_version: int, update_fields: dict[str, Any]
    ) -> bool:
        """Executes a CAS update on a receipt."""
        ...
