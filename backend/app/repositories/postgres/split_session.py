from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.split_session import SplitSession
from app.repositories.interfaces.split_session import SplitSessionRepository
from app.repositories.postgres.base import PostgresRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


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
