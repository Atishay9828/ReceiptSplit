from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from app.models.receipt_edit import ReceiptEdit
from app.repositories.interfaces.receipt_edit import ReceiptEditRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class PostgresReceiptEditRepository(ReceiptEditRepository):
    async def append_in_tx(
        self,
        db: AsyncSession,
        receipt_id: UUID,
        participant_id: UUID,
        field: str,
        old_value: str | None,
        new_value: str | None,
    ) -> ReceiptEdit:
        result = await db.execute(
            text("""
                INSERT INTO receipt_edits (receipt_id, participant_id, field, old_value, new_value)
                VALUES (:receipt_id, :participant_id, :field, :old_value, :new_value)
                RETURNING id, created_at
            """),
            {
                "receipt_id": str(receipt_id),
                "participant_id": str(participant_id),
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
            },
        )
        row = result.first()
        if not row:
            from app.shared.errors import InternalError

            raise InternalError("Failed to insert receipt_edit")

        # We construct the model instance to fulfill the contract, though usually not strictly needed
        edit = ReceiptEdit(
            id=row.id,
            receipt_id=receipt_id,
            participant_id=participant_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            created_at=row.created_at,
        )
        return edit
