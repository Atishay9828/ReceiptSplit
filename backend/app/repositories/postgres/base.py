from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from sqlalchemy import select, text

from app.database import Base
from app.shared.errors import DomainError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

if True:
    pass

T = TypeVar("T", bound=Base)


class PostgresRepository[T: Base]:
    """Base repository with shared query utilities for PostgreSQL."""

    def __init__(self, model: type[T]) -> None:
        self.model = model

    async def fetch_one(self, db: AsyncSession, id: UUID) -> T:
        """Fetches a single entity by ID. Raises 404 DomainError if not found."""
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        obj = result.scalars().first()
        if obj is None:
            raise DomainError(
                code=f"{self.model.__name__.upper()}_NOT_FOUND",
                message=f"{self.model.__name__} not found.",
            )
        return obj

    async def fetch_optional(self, db: AsyncSession, id: UUID) -> T | None:
        """Fetches a single entity by ID, returning None if not found."""
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def cas_update(
        self,
        db: AsyncSession,
        table: str,
        pk_column: str,
        pk_value: UUID,
        expected_version: int,
        update_fields: dict[str, Any],
        has_updated_at: bool = True,
    ) -> bool:
        """
        Executes an atomic version-checked update (CAS pattern, TXN-1).

        Returns True if updated, False if version mismatch (0 rows).
        """
        set_statements = [f"{col} = :{col}" for col in update_fields]

        if has_updated_at:
            set_statements.append("updated_at = now()")
        set_statements.append("version = version + 1")

        set_clause = ",\n                   ".join(set_statements)

        params = {**update_fields, "pk_value": str(pk_value), "expected_version": expected_version}

        stmt = text(f"""
            UPDATE {table}
            SET    {set_clause}
            WHERE  {pk_column} = :pk_value
              AND  version     = :expected_version
            RETURNING {pk_column}
        """)

        result = await db.execute(stmt, params)
        return result.first() is not None
