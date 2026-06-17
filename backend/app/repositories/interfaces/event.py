from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class EventRepository(Protocol):
    async def append_in_tx(
        self,
        db: AsyncSession,
        room_id: UUID,
        event_type: str,
        actor_id: UUID | None,
        payload: dict[str, Any],
    ) -> int:
        """
        Atomically claims the next sequence number and inserts the event.
        MUST be called within an active transaction.
        Returns the assigned sequence_no.
        """
        ...
