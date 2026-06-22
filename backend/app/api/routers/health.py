from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health check",
    description="Return a minimal process health indicator.",
    response_model=dict[str, str],
)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
