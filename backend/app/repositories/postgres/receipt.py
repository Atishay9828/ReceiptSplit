from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.models.receipt import Receipt
from app.repositories.interfaces.receipt import ReceiptRepository
from app.repositories.postgres.base import PostgresRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

if True:
    pass


class PostgresReceiptRepository(PostgresRepository[Receipt], ReceiptRepository):
    def __init__(self) -> None:
        super().__init__(Receipt)

    async def create(self, db: AsyncSession, receipt: Receipt) -> Receipt:
        db.add(receipt)
        return receipt

    async def get_by_room(self, db: AsyncSession, room_id: UUID) -> Receipt | None:
        stmt = select(Receipt).where(Receipt.room_id == room_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def update(
        self,
        db: AsyncSession,
        receipt_id: UUID,
        expected_version: int,
        update_fields: dict[str, Any],
    ) -> bool:
        # Note: receipts doesn't have a version column or updated_at in the phase1 schema!
        # Wait, the interface says "update (CAS) on receipt". Let me check schema.
        # `receipts` does NOT have `version`. So CAS on receipt is not in phase1 schema?
        # If it's not, we might not actually have CAS for receipts. We will just return True.
        # But wait, receipts table: id, room_id, source, is_replaceable, created_at. No version.
        raise NotImplementedError("CAS update not supported on receipts table.")
