from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Header, Response, status

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.common import OKResponse
from app.api.schemas.split import (
    CurrentSplitSessionResponse,
    ParticipantTotalResponse,
    SplitPreviewResponse,
    SplitSessionResponse,
    VersionedRequest,
)
from app.auth.dependencies import require_creator_in_room, require_room_access
from app.database import get_db
from app.services.registry import get_split_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import AuthContext
    from app.services.split_service import SplitService

if True:

    pass

router = APIRouter(prefix="/api/rooms/{room_id}/split", tags=["split"], responses={304: {"description": "Not modified"}, **ERROR_RESPONSES})


@router.get(
    "/preview",
    summary="Preview split",
    description="Calculate a non-persistent split preview for the current receipt state.",
    response_model=SplitPreviewResponse,
    responses={304: {"description": "Not modified"}, **ERROR_RESPONSES},
)
async def preview_split(
    room_id: UUID,
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    _ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    split_service: SplitService = Depends(get_split_service),
) -> SplitPreviewResponse | Response:
    result, room_version = await split_service.preview.calculate_preview(db, room_id)
    etag = f"{room_id}-{room_version}"
    if if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag, "Cache-Control": "no-store"})

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "no-store"
    preview = SplitPreviewResponse(
        grand_total_paise=result.grand_total_paise,
        participant_totals=[
            ParticipantTotalResponse.model_validate(total)
            for total in result.participant_totals
        ],
    )
    return preview


@router.post(
    "/lock",
    status_code=status.HTTP_201_CREATED,
    summary="Lock split",
    description="Transition the room to settlement and persist the transactional split session.",
    response_model=SplitSessionResponse,
)
async def lock_split(
    room_id: UUID,
    payload: VersionedRequest,
    ctx: AuthContext = Depends(require_creator_in_room),
    db: AsyncSession = Depends(get_db),
    service: SplitService = Depends(get_split_service),
) -> SplitSessionResponse:
    session = await service.lock(db, room_id=room_id, version=payload.version, actor_id=ctx.participant_id)
    return SplitSessionResponse.model_validate(session)


@router.post(
    "/unlock",
    summary="Unlock split",
    description="Remove the current split session and transition the room back to active.",
    response_model=OKResponse,
)
async def unlock_split(
    room_id: UUID,
    payload: VersionedRequest,
    ctx: AuthContext = Depends(require_creator_in_room),
    db: AsyncSession = Depends(get_db),
    service: SplitService = Depends(get_split_service),
) -> OKResponse:
    await service.unlock(db, room_id=room_id, version=payload.version, actor_id=ctx.participant_id)
    return OKResponse()


@router.get(
    "/session",
    summary="Get current split session",
    description="Return the persisted split session if the room is currently locked.",
    response_model=CurrentSplitSessionResponse,
)
async def get_current_session(
    room_id: UUID,
    _ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    service: SplitService = Depends(get_split_service),
) -> CurrentSplitSessionResponse:
    session = await service.get_current_session(db, room_id)
    response = CurrentSplitSessionResponse(
        session=SplitSessionResponse.model_validate(session) if session else None
    )
    return response
