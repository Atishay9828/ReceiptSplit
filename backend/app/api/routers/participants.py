from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.participant import JoinRoomRequest, JoinRoomResponse, ParticipantResponse
from app.auth.dependencies import require_room_access
from app.auth.tokens import hash_token
from app.database import get_db
from app.security.rate_limit import RateLimitRule, client_host, enforce_rate_limit
from app.security.safe import fingerprint
from app.services.registry import get_audit_service, get_participant_service
from app.shared.errors import DomainError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import AuthContext
    from app.services.audit_service import AuditService
    from app.services.participant_service import ParticipantService

if True:
    pass

router = APIRouter(prefix="/api/rooms/{room_id}", tags=["participants"], responses=ERROR_RESPONSES)


@router.post(
    "/join",
    status_code=status.HTTP_201_CREATED,
    summary="Join room",
    description="Join a room using an invite token and receive a participant capability token.",
    response_model=JoinRoomResponse,
)
async def join_room(
    room_id: UUID,
    payload: JoinRoomRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: ParticipantService = Depends(get_participant_service),
    audit: AuditService = Depends(get_audit_service),
) -> JoinRoomResponse:
    enforce_rate_limit(
        request,
        action="participant.join",
        key_parts=[str(room_id), fingerprint(payload.invite_token) or "missing", client_host(request)],
        rule=RateLimitRule(limit=20, window_seconds=3600),
    )
    try:
        participant, raw_token = await service.join_room(
            db,
            room_id=room_id,
            invite_token_hash=hash_token(payload.invite_token),
            nickname=payload.nickname,
            color=payload.color,
        )
    except DomainError as exc:
        if exc.code != "INVALID_TOKEN":
            raise
        await audit.record(
            db,
            action="token.access_failed",
            room_id=room_id,
            actor_type="unknown",
            metadata={"token_fingerprint": fingerprint(payload.invite_token)},
            request=request,
        )
        return JSONResponse(status_code=403, content={"error": exc.to_dict()})  # type: ignore[return-value]
    return JoinRoomResponse(
        participant=ParticipantResponse.model_validate(participant),
        participant_token=raw_token,
    )


@router.get(
    "/participants",
    summary="List participants",
    description="List active participants in the authenticated room.",
    response_model=list[ParticipantResponse],
)
async def list_participants(
    room_id: UUID,
    _ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    service: ParticipantService = Depends(get_participant_service),
) -> list[ParticipantResponse]:
    participants = await service.list_active(db, room_id)
    response = [ParticipantResponse.model_validate(participant) for participant in participants]
    return response
