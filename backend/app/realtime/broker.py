"""
ReceiptSplit — In-Process Room Event Broker

Implements a per-room, per-subscriber asyncio.Queue broker for SSE streaming.

Design:
  - Each subscriber gets its own bounded asyncio.Queue(maxsize=QUEUE_CAPACITY).
  - publish() puts a RoomEventDTO into every subscriber queue for that room.
  - If a subscriber's queue is full at publish time, that subscriber is
    removed immediately. The client must reconnect and replay using its
    last seen sequence_no.  No silent drops while keeping the subscriber alive.
  - subscribe() returns an async context manager that yields an async iterator
    and ensures cleanup on disconnect.
  - Broker is safe for concurrent asyncio use within a single process.

Limitations (documented):
  - In-process only — no multi-instance fanout.
  - Broker state is lost on process restart.
  - Clients recover by calling GET /api/rooms/{room_id}/events?after_sequence=N.
  - This is a best-effort notification layer; the durable room_events table is
    the source of truth.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)

# Max events buffered per subscriber before that subscriber is dropped.
QUEUE_CAPACITY = 256


@dataclass(frozen=True, slots=True)
class RoomEventDTO:
    """Wire-safe event DTO used by the broker and SSE serialiser."""

    id: str          # UUID as str
    room_id: str     # UUID as str
    sequence_no: int
    event_type: str
    actor_id: str | None
    payload: dict[str, Any]
    created_at: datetime


class RoomEventBroker:
    """
    In-process room event broker.

    One broker instance is shared application-wide (singleton via registry).
    """

    def __init__(self) -> None:
        # room_id (str) → set of subscriber queues
        self._subscribers: dict[str, set[asyncio.Queue[RoomEventDTO | None]]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, room_id: UUID, event: RoomEventDTO) -> None:
        """
        Publish an event to all subscribers for the room.

        If a subscriber queue is full, that subscriber is removed (disconnected).
        The client must reconnect and replay from its last known sequence_no.
        """
        room_key = str(room_id)
        async with self._lock:
            subs = self._subscribers.get(room_key)
            if not subs:
                return
            stale: list[asyncio.Queue[RoomEventDTO | None]] = []
            for queue in list(subs):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Subscriber is too slow. Remove it so it must reconnect.
                    logger.warning(
                        "SSE subscriber queue full for room %s — disconnecting subscriber",
                        room_id,
                    )
                    stale.append(queue)
                    try:
                        queue.put_nowait(None)  # sentinel: tell iterator to stop
                    except asyncio.QueueFull:
                        # Make room for the sentinel
                        import contextlib
                        with contextlib.suppress(asyncio.QueueEmpty, asyncio.QueueFull):
                            queue.get_nowait()
                            queue.put_nowait(None)
            for queue in stale:
                subs.discard(queue)

    @asynccontextmanager
    async def subscribe(
        self, room_id: UUID
    ) -> AsyncIterator[AsyncIterator[RoomEventDTO]]:
        """
        Async context manager that yields an async iterator of events for the room.

        Usage::

            async with broker.subscribe(room_id) as events:
                async for event in events:
                    yield format_sse(event)

        Cleanup (unsubscribe) is guaranteed on exit, even if the client disconnects.
        """
        room_key = str(room_id)
        queue: asyncio.Queue[RoomEventDTO | None] = asyncio.Queue(maxsize=QUEUE_CAPACITY)

        async with self._lock:
            if room_key not in self._subscribers:
                self._subscribers[room_key] = set()
            self._subscribers[room_key].add(queue)

        try:
            yield _queue_iterator(queue)
        finally:
            async with self._lock:
                subs = self._subscribers.get(room_key)
                if subs:
                    subs.discard(queue)
                    if not subs:
                        del self._subscribers[room_key]

    @property
    def subscriber_count(self) -> int:
        """Total subscriber count across all rooms (for diagnostics)."""
        return sum(len(subs) for subs in self._subscribers.values())


async def _queue_iterator(
    queue: asyncio.Queue[RoomEventDTO | None],
) -> AsyncIterator[RoomEventDTO]:
    """Yield events from the queue until a sentinel (None) is received."""
    while True:
        item = await queue.get()
        if item is None:
            # Sentinel: broker disconnected this subscriber (queue overflow).
            return
        yield item
