from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.participant import ParticipantResponse
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
from app.domain.settlement import SettlementNotReadyError
from app.repositories.postgres.adjustment import PostgresAdjustmentRepository
from app.repositories.postgres.assignment import PostgresAssignmentRepository
from app.repositories.postgres.item import PostgresItemRepository
from app.security.rate_limit import RateLimitRule, client_host, enforce_rate_limit
from app.security.safe import fingerprint
from app.services.registry import (
    get_audit_service,
    get_participant_service,
    get_room_service,
    get_settlement_service,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.dependencies import AuthorizedRoomActor
    from app.auth.models import AuthContext, RequestAuthContext
    from app.services.audit_service import AuditService
    from app.services.participant_service import ParticipantService
    from app.services.room_service import RoomService
    from app.services.settlement_service import SettlementService

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
    request: Request,
    auth_ctx: RequestAuthContext = Depends(get_request_auth_context),
    db: AsyncSession = Depends(get_db),
    service: RoomService = Depends(get_room_service),
) -> RoomCreateResponse:
    enforce_rate_limit(
        request,
        action="room.create",
        key_parts=[client_host(request), str(auth_ctx.user.id) if auth_ctx.user else "anonymous"],
        rule=RateLimitRule(limit=10, window_seconds=3600),
    )
    room, creator_token, invite_token = await service.create_room(
        db,
        split_mode=payload.split_mode,
        payer_name=payload.payer_name,
        payer_vpa=payload.payer_vpa,
        title=payload.title,
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

    participant_responses = []
    for participant in participants:
        response = ParticipantResponse.model_validate(participant)
        if (
            response.role == "creator"
            and response.nickname == "Creator"
            and room.payer_name
        ):
            response = response.model_copy(update={"nickname": room.payer_name})
        participant_responses.append(response)

    return RoomSummaryResponse(
        room=RoomResponse.model_validate(room),
        participants=participant_responses,
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
    request: Request,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: RoomService = Depends(get_room_service),
    settlement_service: SettlementService = Depends(get_settlement_service),
    audit: AuditService = Depends(get_audit_service),
) -> RoomResponse:
    changes: dict[str, Any] = payload.model_dump(exclude={"version"}, exclude_none=True)
    payer_change = "payer_vpa" in changes or "payer_name" in changes
    if payer_change:
        enforce_rate_limit(
            request,
            action="settlement.payer_details_update",
            key_parts=[str(room_id), str(actor.actor_id), client_host(request)],
            rule=RateLimitRule(limit=5, window_seconds=3600),
        )
        if await settlement_service.has_settlement_requests(db, room_id):
            exc = SettlementNotReadyError(
                "Payer details cannot be changed after settlement requests are prepared."
            )
            await audit.record(
                db,
                action="settlement.payer_details_change_blocked",
                room_id=room_id,
                actor_participant_id=actor.participant.participant_id
                if actor.participant
                else None,
                actor_user_id=actor.user.id if actor.user else None,
                actor_type="creator",
                metadata={
                    "attempted_payee_vpa_fingerprint": fingerprint(str(changes.get("payer_vpa"))),
                    "via": "room_patch",
                },
                request=request,
            )
            return JSONResponse(status_code=422, content={"error": exc.to_dict()})  # type: ignore[return-value]

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
