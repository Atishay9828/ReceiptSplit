"""
ReceiptSplit — Room Events API

Three endpoints:

1. GET /api/rooms/{room_id}/events
   Replay endpoint — returns durable events ordered by sequence_no.
   Clients use this to catch up from any point.

2. GET /api/rooms/{room_id}/events/stream
   SSE stream — live event delivery via Server-Sent Events.

   Handoff ordering (subscribe-first approach):
     a. Subscribe to in-process broker FIRST (captures live events going forward).
     b. Replay all durable events with sequence_no > after_sequence (catch-up).
     c. Stream live broker events, deduplicating by sequence_no.

   This approach ensures no events are missed during the replay/subscribe window.
   Deduplication: the set of replayed sequence numbers is tracked; broker events
   with sequence_no already sent are skipped.

   Heartbeat: sent every 15 seconds as an SSE comment (``: heartbeat``).
   Clients should reconnect using the last seen sequence_no if disconnected.

3. GET /api/rooms/{room_id}/events/latest
   Returns the current maximum sequence_no for the room.

Authorization:
  All endpoints require room access (participant token, creator token, or owner JWT).
  Cross-room tokens are rejected. No token → 403.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Query, Header, status
from fastapi.responses import StreamingResponse

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.event import (
    LatestSequenceResponse,
    RoomEventResponse,
    RoomEventsResponse,
)
from app.auth.dependencies import require_room_event_access
from app.database import get_db
from app.services.registry import get_broker, get_event_repo

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import RequestAuthContext
    from app.realtime.broker import RoomEventBroker, RoomEventDTO
    from app.repositories.postgres.event import PostgresEventRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/rooms/{room_id}/events",
    tags=["events"],
    responses=ERROR_RESPONSES,
)

# Maximum value the caller may request for `limit`.
MAX_LIMIT = 500
# SSE heartbeat interval in seconds.
HEARTBEAT_INTERVAL = 15


# ── Helpers ────────────────────────────────────────────────────────────────────


def _event_to_response(event) -> RoomEventResponse:  # type: ignore[no-untyped-def]
    """Convert a RoomEvent ORM row to an API response schema."""
    return RoomEventResponse.model_validate(event)


def _dto_to_sse(dto: RoomEventDTO) -> str:
    """Format a RoomEventDTO as an SSE message string."""
    data = {
        "id": dto.id,
        "room_id": dto.room_id,
        "sequence_no": dto.sequence_no,
        "event_type": dto.event_type,
        "actor_id": dto.actor_id,
        "payload": dto.payload,
        "created_at": dto.created_at.isoformat(),
    }
    return f"id: {dto.sequence_no}\nevent: {dto.event_type}\ndata: {json.dumps(data)}\n\n"


def _orm_to_sse(event: RoomEventResponse) -> str:
    """Format a RoomEventResponse as an SSE message string."""
    data = {
        "id": str(event.id),
        "room_id": str(event.room_id),
        "sequence_no": event.sequence_no,
        "event_type": event.event_type,
        "actor_id": str(event.actor_id) if event.actor_id else None,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }
    return f"id: {event.sequence_no}\nevent: {event.event_type}\ndata: {json.dumps(data)}\n\n"


# ── 1. Event Replay ─────────────────────────────────────────────────────────────


@router.get(
    "",
    summary="List room events",
    description=(
        "Returns committed room events ordered by sequence_no ascending. "
        "Use `after_sequence=0` (default) for a full history fetch, or provide "
        "the last seen sequence_no to receive only newer events. "
        "Requires room access (participant token, creator token, or owner JWT)."
    ),
    response_model=RoomEventsResponse,
)
async def list_room_events(
    room_id: UUID,
    after_sequence: int = Query(
        default=0, ge=0, description="Exclusive lower bound on sequence_no"
    ),
    limit: int = Query(
        default=100, ge=1, le=MAX_LIMIT, description="Max events to return (1–500)"
    ),
    _ctx: RequestAuthContext = Depends(require_room_event_access),
    db: AsyncSession = Depends(get_db),
    event_repo: PostgresEventRepository = Depends(get_event_repo),
) -> RoomEventsResponse:
    rows = await event_repo.list_after(db, room_id, after_sequence, limit)
    latest = await event_repo.get_latest_sequence(db, room_id)
    return RoomEventsResponse(
        room_id=room_id,
        after_sequence=after_sequence,
        latest_sequence=latest,
        events=[_event_to_response(r) for r in rows],
    )


# ── 2. Latest Sequence ──────────────────────────────────────────────────────────


@router.get(
    "/latest",
    summary="Get latest event sequence",
    description="Returns the current maximum committed sequence_no for the room.",
    response_model=LatestSequenceResponse,
)
async def get_latest_sequence(
    room_id: UUID,
    _ctx: RequestAuthContext = Depends(require_room_event_access),
    db: AsyncSession = Depends(get_db),
    event_repo: PostgresEventRepository = Depends(get_event_repo),
) -> LatestSequenceResponse:
    latest = await event_repo.get_latest_sequence(db, room_id)
    return LatestSequenceResponse(room_id=room_id, latest_sequence=latest)


# ── 3. SSE Stream ───────────────────────────────────────────────────────────────


@router.get(
    "/stream",
    summary="Stream room events (SSE)",
    description=(
        "Server-Sent Events stream for real-time room collaboration.\n\n"
        "**Behaviour**:\n"
        "1. Subscribe to the in-process event broker (captures live events).\n"
        "2. Replay all committed events with `sequence_no > after_sequence`.\n"
        "3. Stream incoming broker events, deduplicating by `sequence_no`.\n\n"
        "**SSE format**:\n"
        "```\n"
        "id: 8\n"
        "event: item.claimed\n"
        "data: {...}\n\n"
        ": heartbeat\n\n"
        "```\n\n"
        "**Reconnection**: on disconnect, reconnect with `after_sequence=<last_seen_seq>`. "
        "If the broker drops your subscription due to queue overflow you will receive "
        "no further events on this connection — reconnect and replay.\n\n"
        "**Auth**: participant token, creator token, or owner JWT for this room.\n"
        "Cross-room tokens are rejected."
    ),
    status_code=status.HTTP_200_OK,
    # SSE response — not a JSON model, so no response_model
)
async def stream_room_events(
    room_id: UUID,
    after_sequence: int = Query(default=0, ge=0, description="Exclusive lower bound for replay"),
    _ctx: RequestAuthContext = Depends(require_room_event_access),
    db: AsyncSession = Depends(get_db),
    event_repo: PostgresEventRepository = Depends(get_event_repo),
    broker: RoomEventBroker = Depends(get_broker),
    x_test_no_live: bool = Header(False, alias="X-Test-No-Live"),
) -> StreamingResponse:
    # Snapshot the durable replay rows before the SSE generator runs.
    replay_rows = await event_repo.list_after(db, room_id, after_sequence, limit=MAX_LIMIT)
    replay_events = [_event_to_response(r) for r in replay_rows]

    async def event_generator() -> AsyncIterator[str]:
        # Subscribe to broker FIRST so we capture live events during replay.
        async with broker.subscribe(room_id) as live_stream:
            # Track sent sequence numbers to deduplicate replay / live overlap.
            sent_seqs: set[int] = set()

            # Phase A: replay missed durable events.
            for event in replay_events:
                sent_seqs.add(event.sequence_no)
                yield _orm_to_sse(event)

            if x_test_no_live:
                return

            # Phase B: stream live broker events.

            async def _heartbeat_generator() -> AsyncIterator[str]:
                """Interleave heartbeats every HEARTBEAT_INTERVAL seconds."""
                while True:
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    yield ": heartbeat\n\n"

            # Use asyncio to multiplex the live stream and heartbeat.
            live_queue: asyncio.Queue[str | None] = asyncio.Queue()

            async def _drain_live() -> None:
                try:
                    async for dto in live_stream:
                        if dto.sequence_no not in sent_seqs:
                            sent_seqs.add(dto.sequence_no)
                            await live_queue.put(_dto_to_sse(dto))
                except Exception:
                    logger.debug("SSE live drain ended for room %s", room_id)
                finally:
                    await live_queue.put(None)  # signal end

            async def _drain_heartbeat() -> None:
                try:
                    while True:
                        await asyncio.sleep(HEARTBEAT_INTERVAL)
                        await live_queue.put(": heartbeat\n\n")
                except asyncio.CancelledError:
                    pass

            drain_task = asyncio.create_task(_drain_live())
            hb_task = asyncio.create_task(_drain_heartbeat())

            try:
                while True:
                    msg = await live_queue.get()
                    if msg is None:
                        # Subscriber was disconnected by broker (queue overflow)
                        # or the live stream ended.
                        break
                    yield msg
            finally:
                drain_task.cancel()
                hb_task.cancel()
                # Suppress cancellation exceptions from background tasks.
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await drain_task
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await hb_task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
        },
    )
