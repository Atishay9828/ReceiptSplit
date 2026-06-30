from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, status

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.room import (
    RoomCreateRequest,
    RoomCreateResponse,
    RoomResponse,
    RoomSummaryResponse,
    RoomUpdateRequest,
)
from app.auth.dependencies import (
    attach_room_owner,
    get_request_auth_context,
    require_room_access,
    require_room_event_access,
    require_room_owner_or_creator,
)
from app.database import get_db
from app.repositories.postgres.adjustment import PostgresAdjustmentRepository
from app.repositories.postgres.assignment import PostgresAssignmentRepository
from app.repositories.postgres.item import PostgresItemRepository
from app.services.registry import get_participant_service, get_room_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.dependencies import AuthorizedRoomActor
    from app.auth.models import AuthContext, RequestAuthContext
    from app.services.participant_service import ParticipantService
    from app.services.room_service import RoomService

if True:
    pass

router = APIRouter(prefix="/api/rooms", tags=["rooms"], responses=ERROR_RESPONSES)
_item_repo = PostgresItemRepository()
_adjustment_repo = PostgresAdjustmentRepository()
_assignment_repo = PostgresAssignmentRepository()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create room",
    description="Create a draft room with creator and invite capability tokens.",
    response_model=RoomCreateResponse,
)
async def create_room(
    payload: RoomCreateRequest,
    auth_ctx: RequestAuthContext = Depends(get_request_auth_context),
    db: AsyncSession = Depends(get_db),
    service: RoomService = Depends(get_room_service),
) -> RoomCreateResponse:
    room, creator_token, invite_token = await service.create_room(
        db, split_mode=payload.split_mode
    )
    if auth_ctx.user is not None:
        await attach_room_owner(room.id, auth_ctx.user, db)
    return RoomCreateResponse(
        room=RoomResponse.model_validate(room),
        creator_token=creator_token,
        invite_token=invite_token,
    )


@router.get(
    "/{room_id}",
    summary="Get room",
    description="Fetch the authenticated participant's room metadata.",
    response_model=RoomResponse,
)
async def get_room(
    room_id: UUID,
    _ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    service: RoomService = Depends(get_room_service),
) -> RoomResponse:
    room = await service.get_room(db, room_id)
    response = RoomResponse.model_validate(room)
    return response


@router.get(
    "/{room_id}/summary",
    summary="Get room summary",
    description="Fetch room metadata and current collaboration state for frontend rendering.",
    response_model=RoomSummaryResponse,
)
async def get_room_summary(
    room_id: UUID,
    _ctx: RequestAuthContext = Depends(require_room_event_access),
    db: AsyncSession = Depends(get_db),
    room_service: RoomService = Depends(get_room_service),
    participant_service: ParticipantService = Depends(get_participant_service),
) -> RoomSummaryResponse:
    room = await room_service.get_room(db, room_id)
    receipt = await room_service.get_receipt(db, room_id)
    participants = await participant_service.list_active(db, room_id)
    items = await _item_repo.list_by_receipt(db, receipt.id)
    adjustments = await _adjustment_repo.list_by_room(db, room_id)
    assignments = await _assignment_repo.list_by_room(db, room_id)

    return RoomSummaryResponse(
        room=RoomResponse.model_validate(room),
        participants=list(participants),
        items=list(items),
        adjustments=list(adjustments),
        assignments=list(assignments),
    )


@router.patch(
    "/{room_id}",
    summary="Update room",
    description="Update creator-controlled room metadata or perform a state transition.",
    response_model=RoomResponse,
)
async def update_room(
    room_id: UUID,
    payload: RoomUpdateRequest,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: RoomService = Depends(get_room_service),
) -> RoomResponse:
    changes: dict[str, Any] = payload.model_dump(exclude={"version"}, exclude_none=True)

    if "status" in changes:
        if len(changes) > 1:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400, detail="Cannot mix status update with other fields"
            )

        target_status = changes["status"]
        if target_status in ("settled", "expired"):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400, detail=f"Status {target_status} cannot be set manually via PATCH"
            )

        room = await service.transition_room(
            db,
            room_id=room_id,
            expected_version=payload.version,
            to_state=target_status,
            actor_id=actor.actor_id,
        )
    else:
        if not changes:
            room = await service.get_room(db, room_id)
        else:
            room = await service.update_room(
                db,
                room_id=room_id,
                expected_version=payload.version,
                actor_id=actor.actor_id,
                update_fields=changes,
            )
    response = RoomResponse.model_validate(room)
    return response
