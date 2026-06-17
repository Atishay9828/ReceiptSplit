from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.line_item import LineItem


class ItemRepository(Protocol):
    async def create(self, db: AsyncSession, item: LineItem) -> LineItem:
        """Persists a new line item."""
        ...

    async def get(self, db: AsyncSession, item_id: UUID) -> LineItem | None:
        """Retrieves a line item by ID."""
        ...

    async def update(
        self, db: AsyncSession, item_id: UUID, expected_version: int, update_fields: dict[str, Any]
    ) -> bool:
        """Executes a CAS update on a line item."""
        ...

    async def soft_delete(self, db: AsyncSession, item_id: UUID, expected_version: int) -> bool:
        """Soft-deletes a line item."""
        ...
