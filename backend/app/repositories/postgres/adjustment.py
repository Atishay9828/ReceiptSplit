from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text

from app.models.split_adjustment import SplitAdjustment
from app.repositories.interfaces.adjustment import AdjustmentRepository
from app.repositories.postgres.base import PostgresRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

if True:
    pass


class PostgresAdjustmentRepository(PostgresRepository[SplitAdjustment], AdjustmentRepository):
    def __init__(self) -> None:
        super().__init__(SplitAdjustment)

    async def create(self, db: AsyncSession, adjustment: SplitAdjustment) -> SplitAdjustment:
        db.add(adjustment)
        return adjustment

    async def list_by_room(self, db: AsyncSession, room_id: UUID) -> list[SplitAdjustment]:
        stmt = (
            select(SplitAdjustment)
            .where(SplitAdjustment.room_id == room_id, SplitAdjustment.deleted_at.is_(None))
            .order_by(SplitAdjustment.sort_order)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        db: AsyncSession,
        adjustment_id: UUID,
        expected_version: int,
        update_fields: dict[str, Any],
    ) -> bool:
        return await self.cas_update(
            db,
            table="split_adjustments",
            pk_column="id",
            pk_value=adjustment_id,
            expected_version=expected_version,
            update_fields=update_fields,
            has_updated_at=False,
        )

    async def soft_delete(
        self, db: AsyncSession, adjustment_id: UUID, expected_version: int
    ) -> bool:
        stmt = text("""
            UPDATE split_adjustments
            SET deleted_at = now(),
                version = version + 1
            WHERE id = :id AND version = :expected_version
            RETURNING id
        """)
        result = await db.execute(
            stmt, {"id": str(adjustment_id), "expected_version": expected_version}
        )
        return result.first() is not None
