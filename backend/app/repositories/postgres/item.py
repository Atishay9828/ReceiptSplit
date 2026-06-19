from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.models.line_item import LineItem
from app.repositories.interfaces.item import ItemRepository
from app.repositories.postgres.base import PostgresRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class PostgresItemRepository(PostgresRepository[LineItem], ItemRepository):
    def __init__(self) -> None:
        super().__init__(LineItem)

    async def create(self, db: AsyncSession, item: LineItem) -> LineItem:
        db.add(item)
        return item

    async def get(self, db: AsyncSession, item_id: UUID) -> LineItem | None:
        return await self.fetch_optional(db, item_id)

    async def update(
        self, db: AsyncSession, item_id: UUID, expected_version: int, update_fields: dict[str, Any]
    ) -> bool:
        return await self.cas_update(
            db,
            table="line_items",
            pk_column="id",
            pk_value=item_id,
            expected_version=expected_version,
            update_fields=update_fields,
            has_updated_at=False,  # line_items has deleted_at, not updated_at
        )

    async def soft_delete(self, db: AsyncSession, item_id: UUID, expected_version: int) -> bool:
        from sqlalchemy import text

        stmt = text("""
            UPDATE line_items
            SET deleted_at = now(),
                version = version + 1
            WHERE id = :id AND version = :expected_version
            RETURNING id
        """)
        result = await db.execute(stmt, {"id": str(item_id), "expected_version": expected_version})
        return result.first() is not None

    async def list_by_receipt(self, db: AsyncSession, receipt_id: UUID) -> list[LineItem]:
        stmt = (
            select(LineItem)
            .where(LineItem.receipt_id == receipt_id, LineItem.deleted_at.is_(None))
            .order_by(LineItem.sort_order)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
