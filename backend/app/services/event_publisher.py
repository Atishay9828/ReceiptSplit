
"""
ReceiptSplit — Two-Phase Event Publisher

Phase 1 (in-transaction): Writes event record via EventRepository.append_in_tx().
Phase 2 (post-commit):    Broadcasts via Supabase Realtime (best-effort stub).

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
            seq = await publisher.append_in_tx(db, room_id, "item.created", actor_id, payload)
        # transaction committed
        await publisher.broadcast(room_id, "item.created", payload, seq)
    """

    def __init__(self, event_repo: EventRepository) -> None:
        self._event_repo = event_repo

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

        Defers the broadcast to be sent after the transaction commits.
        """
        seq = await self._event_repo.append_in_tx(
            db, room_id, event_type, actor_id, payload,
        )
        if "deferred_events" not in db.info:
            db.info["deferred_events"] = []
        db.info["deferred_events"].append((room_id, event_type, payload, seq))
        return seq

    async def flush_deferred_events(self, db: AsyncSession) -> None:
        """
        Broadcasts all deferred events for this session.
        Called AFTER the transaction commits.
        """
        events = db.info.pop("deferred_events", [])
        for args in events:
            await self.broadcast(*args)

    async def broadcast(self, *args: Any, **kwargs: Any) -> None:
        """
        Deprecated. Broadcasts are now deferred automatically and emitted by
        flush_deferred_events after the transaction commits.
        """
        pass

    async def _do_broadcast(
        self,
        room_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        seq: int,
    ) -> None:
        """
        Broadcasts via Supabase Realtime. Called AFTER transaction commits.

        Phase 1 stub: logs the event. Full implementation deferred to
        the Realtime milestone.

        Failure is non-fatal — clients reconcile via GET /events?since_sequence=N.
        """
        try:
            logger.info(
                "Event broadcast [%s] room=%s seq=%d",
                event_type,
                room_id,
                seq,
            )
            # TODO(realtime): Replace with Supabase channel.send() in Realtime milestone.
        except Exception:
            logger.warning(
                "Realtime broadcast failed for room %s event %s seq %d",
                room_id,
                event_type,
                seq,
                exc_info=True,
            )
