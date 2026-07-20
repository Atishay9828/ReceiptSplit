from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from app.models.split_session import SplitSession
from app.repositories.interfaces.split_session import SplitSessionRepository
from app.repositories.postgres.base import PostgresRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

if True:
    pass


class PostgresSplitSessionRepository(PostgresRepository[SplitSession], SplitSessionRepository):
    def __init__(self) -> None:
        super().__init__(SplitSession)

    async def create(self, db: AsyncSession, session: SplitSession) -> SplitSession:
        db.add(session)
        return session

    async def get_by_room(self, db: AsyncSession, room_id: UUID) -> SplitSession | None:
        stmt = select(SplitSession).where(SplitSession.room_id == room_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def delete_by_room(self, db: AsyncSession, room_id: UUID) -> bool:
        stmt = (
            delete(SplitSession).where(SplitSession.room_id == room_id).returning(SplitSession.id)
        )
        result = await db.execute(stmt)
        return result.first() is not None
