from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, status

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.participant import JoinRoomRequest, JoinRoomResponse, ParticipantResponse
from app.auth.dependencies import require_room_access
from app.auth.tokens import hash_token
from app.database import get_db
from app.services.registry import get_participant_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import AuthContext
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
    db: AsyncSession = Depends(get_db),
    service: ParticipantService = Depends(get_participant_service),
) -> JoinRoomResponse:
    participant, raw_token = await service.join_room(
        db,
        room_id=room_id,
        invite_token_hash=hash_token(payload.invite_token),
        nickname=payload.nickname,
        color=payload.color,
    )
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
