"""
ReceiptSplit — Service Registry

Lightweight wiring module that constructs service instances with their
repository dependencies. No DI container — just factory functions.

Usage:
    from app.services.registry import get_room_service, get_item_service
"""

from __future__ import annotations

from functools import lru_cache
from typing import TypedDict

from app.config import settings
from app.ocr.parser import IndianRestaurantReceiptParser
from app.ocr.preprocessing import BasicReceiptPreprocessor
from app.ocr.providers import MockOcrProvider, TesseractOcrProvider
from app.ocr.service import ReceiptOcrService
from app.ocr.storage import LocalReceiptImageStorage
from app.ocr.validation import ImageValidationConfig, ReceiptImageValidator
from app.realtime.broker import RoomEventBroker
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
from app.services.abuse_service import AbuseService
from app.services.adjustment_service import AdjustmentService
from app.services.audit_service import AuditService
from app.services.event_publisher import EventPublisher
from app.services.item_service import ItemService
from app.services.participant_service import ParticipantService
from app.services.room_service import RoomService
from app.services.settlement_service import SettlementService
from app.services.split_service import (
    SplitLockCoordinator,
    SplitPreviewService,
    SplitService,
)


class RepositoryRegistry(TypedDict):
    room: PostgresRoomRepository
    receipt: PostgresReceiptRepository
    participant: PostgresParticipantRepository
    item: PostgresItemRepository
    adjustment: PostgresAdjustmentRepository
    assignment: PostgresAssignmentRepository
    event: PostgresEventRepository
    receipt_edit: PostgresReceiptEditRepository
    split_session: PostgresSplitSessionRepository


# ── Singleton repositories ───────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _repos() -> RepositoryRegistry:
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
def get_broker() -> RoomEventBroker:
    """Return the singleton in-process event broker."""
    return RoomEventBroker()


@lru_cache(maxsize=1)
def get_event_publisher() -> EventPublisher:
    return EventPublisher(event_repo=_repos()["event"], broker=get_broker())


@lru_cache(maxsize=1)
def get_event_repo() -> PostgresEventRepository:
    """Return the singleton event repository (for the replay endpoint)."""
    return _repos()["event"]


@lru_cache(maxsize=1)
def get_audit_service() -> AuditService:
    return AuditService()


@lru_cache(maxsize=1)
def get_abuse_service() -> AbuseService:
    return AbuseService(audit_service=get_audit_service())


# ── Service factories ────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_room_service() -> RoomService:
    r = _repos()
    return RoomService(
        room_repo=r["room"],
        receipt_repo=r["receipt"],
        participant_repo=r["participant"],
        event_publisher=get_event_publisher(),
        audit_service=get_audit_service(),
    )


@lru_cache(maxsize=1)
def get_participant_service() -> ParticipantService:
    r = _repos()
    return ParticipantService(
        participant_repo=r["participant"],
        assignment_repo=r["assignment"],
        room_repo=r["room"],
        event_publisher=get_event_publisher(),
        audit_service=get_audit_service(),
    )


@lru_cache(maxsize=1)
def get_item_service() -> ItemService:
    r = _repos()
    return ItemService(
        item_repo=r["item"],
        assignment_repo=r["assignment"],
        receipt_edit_repo=r["receipt_edit"],
        room_repo=r["room"],
        event_publisher=get_event_publisher(),
    )


@lru_cache(maxsize=1)
def get_adjustment_service() -> AdjustmentService:
    r = _repos()
    return AdjustmentService(
        adjustment_repo=r["adjustment"],
        receipt_edit_repo=r["receipt_edit"],
        room_repo=r["room"],
        event_publisher=get_event_publisher(),
    )


@lru_cache(maxsize=1)
def get_split_service() -> SplitService:
    r = _repos()
    ep = get_event_publisher()
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


@lru_cache(maxsize=1)
def get_settlement_service() -> SettlementService:
    r = _repos()
    return SettlementService(
        room_repo=r["room"],
        session_repo=r["split_session"],
        event_publisher=get_event_publisher(),
        audit_service=get_audit_service(),
    )


@lru_cache(maxsize=1)
def get_ocr_service() -> ReceiptOcrService:
    r = _repos()
    validator = ReceiptImageValidator(
        ImageValidationConfig(
            max_bytes=settings.ocr_max_image_bytes,
            max_width=settings.ocr_max_width,
            max_height=settings.ocr_max_height,
        )
    )
    provider = (
        MockOcrProvider()
        if settings.ocr_provider == "mock"
        else TesseractOcrProvider(
            tesseract_cmd=settings.tesseract_cmd,
            timeout_seconds=settings.ocr_timeout_seconds,
        )
    )
    return ReceiptOcrService(
        room_repo=r["room"],
        receipt_repo=r["receipt"],
        validator=validator,
        preprocessor=BasicReceiptPreprocessor(validator),
        storage=LocalReceiptImageStorage(settings.ocr_local_storage_dir),
        provider=provider,
        parser=IndianRestaurantReceiptParser(),
        event_publisher=get_event_publisher(),
        store_raw_text=settings.ocr_store_raw_text,
    )
