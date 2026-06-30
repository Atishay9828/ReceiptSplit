from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room_event import RoomEvent


class EventRepository(Protocol):
    async def append_in_tx(
        self,
        db: AsyncSession,
        room_id: UUID,
        event_type: str,
        actor_id: UUID | None,
        payload: dict[str, Any],
    ) -> "AppendResult":
        """
        Atomically claims the next sequence number and inserts the event.
        MUST be called within an active transaction.
        Returns an AppendResult with sequence_no, event id, and created_at.
        """
        ...

    async def list_after(
        self,
        db: AsyncSession,
        room_id: UUID,
        after_sequence: int,
        limit: int,
    ) -> list[RoomEvent]:
        """
        Returns events for room_id with sequence_no > after_sequence,
        ordered by sequence_no ASC, up to limit rows.
        """
        ...

    async def get_latest_sequence(self, db: AsyncSession, room_id: UUID) -> int:
        """
        Returns the highest sequence_no committed for room_id.
        Returns 0 if no events exist yet.
        """
        ...


from dataclasses import dataclass  # noqa: E402
from datetime import datetime  # noqa: E402


@dataclass(frozen=True, slots=True)
class AppendResult:
    """Return value from append_in_tx: the assigned event identity."""

    sequence_no: int
    event_id: str    # UUID as string — safe to pass across asyncio boundaries
    created_at: datetime
