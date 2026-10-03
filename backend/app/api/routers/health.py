from __future__ import annotations

import os

from fastapi import APIRouter, Request

from app.config import settings

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health check",
    description="Return a minimal process health indicator.",
    response_model=dict[str, str],
)
async def health_check(request: Request) -> dict[str, str]:
    return {
        "status": "ok",
        "commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "ocr_provider": settings.ocr_provider,
        "ocr_ready": "true" if getattr(request.app.state, "ocr_ready", False) else "false",
    }
