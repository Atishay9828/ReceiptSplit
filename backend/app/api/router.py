from __future__ import annotations

from fastapi import APIRouter

from app.api.routers import (
    adjustments,
    auth,
    events,
    health,
    items,
    ocr,
    participants,
    rooms,
    split,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(rooms.router)
api_router.include_router(participants.router)
api_router.include_router(items.router)
api_router.include_router(adjustments.router)
api_router.include_router(split.router)
api_router.include_router(events.router)
api_router.include_router(ocr.router)
