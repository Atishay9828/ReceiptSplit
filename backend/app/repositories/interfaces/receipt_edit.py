from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt_edit import ReceiptEdit


class ReceiptEditRepository(Protocol):
    async def append_in_tx(
        self,
        db: AsyncSession,
        receipt_id: UUID,
        participant_id: UUID,
        field: str,
        old_value: str | None,
        new_value: str | None,
    ) -> ReceiptEdit:
        """Records an audit row in the same transaction as the mutation."""
        ...
