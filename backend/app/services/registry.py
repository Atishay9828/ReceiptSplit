"""
ReceiptSplit — Service Registry

Lightweight wiring module that constructs service instances with their
repository dependencies. No DI container — just factory functions.

Usage:
    from app.services.registry import get_room_service, get_item_service
"""

from __future__ import annotations

from functools import lru_cache

from app.repositories.postgres import (
    PostgresAdjustmentRepository,
    PostgresAssignmentRepository,
    PostgresEventRepository,
    PostgresItemRepository,
    PostgresParticipantRepository,
    PostgresReceiptEditRepository,
    PostgresReceiptRepository,
    PostgresRoomRepository,
    PostgresSplitSessionRepository,
)
from app.services.adjustment_service import AdjustmentService
from app.services.event_publisher import EventPublisher
from app.services.item_service import ItemService
from app.services.participant_service import ParticipantService
from app.services.room_service import RoomService
from app.services.split_service import (
    SplitLockCoordinator,
    SplitPreviewService,
    SplitService,
)

# ── Singleton repositories ───────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _repos() -> dict:
    return {
        "room": PostgresRoomRepository(),
        "receipt": PostgresReceiptRepository(),
        "participant": PostgresParticipantRepository(),
        "item": PostgresItemRepository(),
        "adjustment": PostgresAdjustmentRepository(),
        "assignment": PostgresAssignmentRepository(),
        "event": PostgresEventRepository(),
        "receipt_edit": PostgresReceiptEditRepository(),
        "split_session": PostgresSplitSessionRepository(),
    }


@lru_cache(maxsize=1)
def _event_publisher() -> EventPublisher:
    return EventPublisher(event_repo=_repos()["event"])


# ── Service factories ────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_room_service() -> RoomService:
    r = _repos()
    return RoomService(
        room_repo=r["room"],
        receipt_repo=r["receipt"],
        participant_repo=r["participant"],
        event_publisher=_event_publisher(),
    )


@lru_cache(maxsize=1)
def get_participant_service() -> ParticipantService:
    return ParticipantService(
        participant_repo=_repos()["participant"],
        event_publisher=_event_publisher(),
    )


@lru_cache(maxsize=1)
def get_item_service() -> ItemService:
    r = _repos()
    return ItemService(
        item_repo=r["item"],
        assignment_repo=r["assignment"],
        receipt_edit_repo=r["receipt_edit"],
        room_repo=r["room"],
        event_publisher=_event_publisher(),
    )


@lru_cache(maxsize=1)
def get_adjustment_service() -> AdjustmentService:
    r = _repos()
    return AdjustmentService(
        adjustment_repo=r["adjustment"],
        receipt_edit_repo=r["receipt_edit"],
        event_publisher=_event_publisher(),
    )


@lru_cache(maxsize=1)
def get_split_service() -> SplitService:
    r = _repos()
    ep = _event_publisher()
    coordinator = SplitLockCoordinator(
        room_repo=r["room"],
        receipt_repo=r["receipt"],
        item_repo=r["item"],
        participant_repo=r["participant"],
        adjustment_repo=r["adjustment"],
        assignment_repo=r["assignment"],
        session_repo=r["split_session"],
        event_publisher=ep,
    )
    preview = SplitPreviewService(
        room_repo=r["room"],
        receipt_repo=r["receipt"],
        item_repo=r["item"],
        participant_repo=r["participant"],
        adjustment_repo=r["adjustment"],
        assignment_repo=r["assignment"],
        session_repo=r["split_session"],
    )
    return SplitService(lock_coordinator=coordinator, preview=preview)
