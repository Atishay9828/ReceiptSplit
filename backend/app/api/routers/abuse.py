from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Request, status

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.abuse import AbuseReportRequest, AbuseReportResponse
from app.auth.dependencies import require_room_event_access
from app.database import get_db
from app.security.rate_limit import RateLimitRule, client_host, enforce_rate_limit
from app.services.registry import get_abuse_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import RequestAuthContext
    from app.services.abuse_service import AbuseService


router = APIRouter(prefix="/api/rooms/{room_id}", tags=["abuse"], responses=ERROR_RESPONSES)


@router.post(
    "/abuse-reports",
    status_code=status.HTTP_201_CREATED,
    response_model=AbuseReportResponse,
    summary="Submit an abuse report",
)
async def submit_abuse_report(
    room_id: UUID,
    payload: AbuseReportRequest,
    request: Request,
    ctx: RequestAuthContext = Depends(require_room_event_access),
    db: AsyncSession = Depends(get_db),
    service: AbuseService = Depends(get_abuse_service),
) -> AbuseReportResponse:
    enforce_rate_limit(
        request,
        action="abuse.report",
        key_parts=[str(room_id), client_host(request)],
        rule=RateLimitRule(limit=5, window_seconds=3600),
    )
    report = await service.report(
        db,
        room_id=room_id,
        ctx=ctx,
        reason=payload.reason,
        message=payload.message,
    )
    return AbuseReportResponse(
        id=report.id,
        room_id=report.room_id,
        reason=payload.reason,
        message=report.message,
        created_at=report.created_at,
    )
