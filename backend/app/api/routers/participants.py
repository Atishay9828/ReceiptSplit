from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.participant import JoinRoomRequest, JoinRoomResponse, ParticipantResponse
from app.auth.dependencies import (
    AuthorizedRoomActor,
    require_room_access,
    require_room_owner_or_creator,
)
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
        key_parts=[
            str(room_id),
            fingerprint(payload.invite_token) or "missing",
            client_host(request),
        ],
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
    response_model=list[ParticipantResponse],
    summary="List active participants",
    description="Returns all participants currently in the room who have not left.",
)
async def list_participants(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: ParticipantService = Depends(get_participant_service),
    auth: AuthContext = Depends(require_room_access),
) -> list[ParticipantResponse]:
    participants = await service.list_active(db, room_id)
    return [ParticipantResponse.model_validate(p) for p in participants]


@router.delete(
    "/participants/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove participant",
    description="Removes a participant from the room. Requires creator access.",
)
async def remove_participant(
    room_id: UUID,
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: ParticipantService = Depends(get_participant_service),
    auth: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
) -> None:
    await service.remove_participant(
        db,
        room_id=room_id,
        participant_id=participant_id,
        actor_id=auth.actor_id,
    )
