"""ReceiptSplit — API schemas for room event replay and streaming endpoints."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict


class RoomEventResponse(BaseModel):
    """Single room event as returned by the replay and stream endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    room_id: UUID
    sequence_no: int
    event_type: str
    actor_id: UUID | None
    payload: dict[str, Any]
    created_at: datetime


class RoomEventsResponse(BaseModel):
    """Paginated event list response for GET /api/rooms/{room_id}/events."""

    room_id: UUID
    after_sequence: int
    latest_sequence: int
    events: list[RoomEventResponse]


class LatestSequenceResponse(BaseModel):
    """Response for GET /api/rooms/{room_id}/events/latest."""

    room_id: UUID
    latest_sequence: int
