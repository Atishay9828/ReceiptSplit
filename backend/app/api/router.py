from __future__ import annotations

from fastapi import APIRouter

from app.api.routers import adjustments, health, items, participants, rooms, split

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(rooms.router)
api_router.include_router(participants.router)
api_router.include_router(items.router)
api_router.include_router(adjustments.router)
api_router.include_router(split.router)
