from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text

from app.models.room_event import RoomEvent
from app.repositories.interfaces.event import AppendResult, EventRepository
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
    ) -> AppendResult:
        """
        Atomically claims the next sequence number and inserts the event row.
        Uses RETURNING id, created_at so the publisher can build a full DTO
        from committed data — no re-fetch required after commit.

        MUST be called within an active transaction (begin_nested savepoint).
        """
        # Step 1: Increment the per-room counter and claim next_seq.
        seq_result = await db.execute(
            text("""
                UPDATE room_sequences SET next_seq = next_seq + 1
                WHERE room_id = :room_id
                RETURNING next_seq
            """),
            {"room_id": str(room_id)},
        )
        row = seq_result.first()
        if row is None:
            raise InternalError(f"No room_sequence row for room {room_id}")
        seq = row.next_seq

        # Step 2: Insert the event and capture its generated id + server timestamp.
        insert_result = await db.execute(
            text("""
                INSERT INTO room_events (room_id, event_type, actor_id, payload, sequence_no)
                VALUES (:room_id, :event_type, :actor_id, :payload, :seq)
                RETURNING id, created_at
            """),
            {
                "room_id": str(room_id),
                "event_type": event_type,
                "actor_id": str(actor_id) if actor_id else None,
                "payload": json.dumps(payload),
                "seq": seq,
            },
        )
        insert_row = insert_result.first()
        if insert_row is None:
            raise InternalError(f"INSERT INTO room_events returned no row for room {room_id}")

        return AppendResult(
            sequence_no=seq,
            event_id=str(insert_row.id),
            created_at=insert_row.created_at,
        )

    async def list_after(
        self,
        db: AsyncSession,
        room_id: UUID,
        after_sequence: int,
        limit: int,
    ) -> list[RoomEvent]:
        """
        Returns up to `limit` events for room_id with sequence_no > after_sequence,
        ordered ascending.  Uses the covering idx_events_room_seq index.
        """
        result = await db.execute(
            select(RoomEvent)
            .where(
                RoomEvent.room_id == room_id,
                RoomEvent.sequence_no > after_sequence,
            )
            .order_by(RoomEvent.sequence_no.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_sequence(self, db: AsyncSession, room_id: UUID) -> int:
        """
        Returns the highest committed sequence_no for room_id.
        Returns 0 if no events exist yet.
        """
        result = await db.execute(
            text("""
                SELECT COALESCE(MAX(sequence_no), 0) AS latest
                FROM room_events
                WHERE room_id = :room_id
            """),
            {"room_id": str(room_id)},
        )
        row = result.first()
        return int(row.latest) if row else 0
