from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from app.repositories.interfaces.event import EventRepository
from app.shared.errors import InternalError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

if True:
    pass


class PostgresEventRepository(EventRepository):
    async def append_in_tx(
        self,
        db: AsyncSession,
        room_id: UUID,
        event_type: str,
        actor_id: UUID | None,
        payload: dict[str, Any],
    ) -> int:
        result = await db.execute(
            text("""
                UPDATE room_sequences SET next_seq = next_seq + 1
                WHERE room_id = :room_id
                RETURNING next_seq
            """),
            {"room_id": str(room_id)},
        )
        row = result.first()
        if row is None:
            raise InternalError(f"No room_sequence row for room {room_id}")
        seq = row.next_seq

        await db.execute(
            text("""
                INSERT INTO room_events (room_id, event_type, actor_id, payload, sequence_no)
                VALUES (:room_id, :event_type, :actor_id, :payload, :seq)
            """),
            {
                "room_id": str(room_id),
                "event_type": event_type,
                "actor_id": str(actor_id) if actor_id else None,
                "payload": json.dumps(payload),
                "seq": seq,
            },
        )
        return seq
