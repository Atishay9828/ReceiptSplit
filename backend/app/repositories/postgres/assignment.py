from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select

from app.models.line_item_assignment import LineItemAssignment
from app.repositories.interfaces.assignment import AssignmentRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

if True:
    pass


class PostgresAssignmentRepository(AssignmentRepository):
    async def create(self, db: AsyncSession, assignment: LineItemAssignment) -> LineItemAssignment:
        db.add(assignment)
        return assignment

    async def delete_by_participant_and_item(
        self, db: AsyncSession, item_id: UUID, participant_id: UUID
    ) -> bool:
        stmt = (
            delete(LineItemAssignment)
            .where(
                LineItemAssignment.line_item_id == item_id,
                LineItemAssignment.participant_id == participant_id,
            )
            .returning(LineItemAssignment.id)
        )
        result = await db.execute(stmt)
        return result.first() is not None

    async def list_by_room(self, db: AsyncSession, room_id: UUID) -> list[LineItemAssignment]:
        stmt = select(LineItemAssignment).where(LineItemAssignment.room_id == room_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_claimed_qty(self, db: AsyncSession, item_id: UUID) -> int:
        stmt = select(func.coalesce(func.sum(LineItemAssignment.claimed_qty), 0)).where(
            LineItemAssignment.line_item_id == item_id
        )
        result = await db.execute(stmt)
        return result.scalar() or 0
