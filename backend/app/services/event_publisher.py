"""
ReceiptSplit — Two-Phase Event Publisher

Phase 1 (in-transaction):
    Writes a durable room_event row via EventRepository.append_in_tx().
    Uses RETURNING id, created_at so the full event DTO is captured at
    insert time — no re-fetch is needed after commit.
    Stores the DTO data in db.info["deferred_events"] for post-commit dispatch.

Phase 2 (post-commit):
    flush_deferred_events() is called by get_db() AFTER the outer transaction
    commits.  It publishes each deferred event to the in-process RoomEventBroker.

Durability guarantee:
    The durable room_events row is the source of truth.
    If broker publish fails the row is still queryable via the replay endpoint.
    If the request transaction rolls back, deferred_events is never populated
    (begin_nested rollback discards db.info writes), so no broker event is emitted.

Design authority:
    - Phase 1 Design Amendments TXN-2
    - PDD §11.1 (realtime events)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.realtime.broker import RoomEventBroker
    from app.repositories.interfaces.event import EventRepository

if True:
    pass

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Two-Phase Event Publisher per TXN-2.

    Usage::

        async with db.begin_nested():
            # ... business mutation ...
            result = await publisher.append_in_tx(db, room_id, "item.created", actor_id, payload)
        # savepoint committed — outer tx still open
        # ...outer tx commits...
        # get_db() calls flush_deferred_events(db)  →  broker.publish()
    """

    def __init__(
        self,
        event_repo: EventRepository,
        broker: RoomEventBroker | None = None,
    ) -> None:
        self._event_repo = event_repo
        self._broker = broker

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
        MUST be called within an active transaction (before commit).

        Captures the committed row's id and created_at via RETURNING, so the
        full RoomEventDTO can be published to the broker post-commit without
        any additional DB round-trip.

        Returns the assigned sequence_no (for backward compatibility with callers
        that pass seq to the legacy broadcast() call).
        """
        result = await self._event_repo.append_in_tx(
            db, room_id, event_type, actor_id, payload,
        )

        # Store the full DTO data keyed by room_id for post-commit dispatch.
        # db.info survives the begin_nested savepoint but is discarded if the
        # outer transaction rolls back — enforcing the durability guarantee.
        if "deferred_events" not in db.info:
            db.info["deferred_events"] = []
        db.info["deferred_events"].append(
            {
                "room_id": room_id,
                "event_type": event_type,
                "actor_id": actor_id,
                "payload": payload,
                "sequence_no": result.sequence_no,
                "event_id": result.event_id,
                "created_at": result.created_at,
            }
        )
        return result.sequence_no

    async def flush_deferred_events(self, db: AsyncSession) -> None:
        """
        Publish all deferred events for this session to the in-process broker.
        Called AFTER the outer transaction commits (by get_db()).

        Failure is non-fatal — committed room_events remain queryable via replay.
        """
        events = db.info.pop("deferred_events", [])
        if not events or self._broker is None:
            return

        from app.realtime.broker import RoomEventDTO

        for ev in events:
            try:
                dto = RoomEventDTO(
                    id=ev["event_id"],
                    room_id=str(ev["room_id"]),
                    sequence_no=ev["sequence_no"],
                    event_type=ev["event_type"],
                    actor_id=str(ev["actor_id"]) if ev["actor_id"] else None,
                    payload=ev["payload"],
                    created_at=ev["created_at"],
                )
                await self._broker.publish(ev["room_id"], dto)
            except Exception:
                logger.warning(
                    "Broker publish failed for room %s event %s seq %d",
                    ev["room_id"],
                    ev["event_type"],
                    ev["sequence_no"],
                    exc_info=True,
                )

    async def broadcast(self, *args: Any, **kwargs: Any) -> None:
        """
        No-op stub retained for backward compatibility with existing service callers.
        Real post-commit delivery is handled by flush_deferred_events().
        """
