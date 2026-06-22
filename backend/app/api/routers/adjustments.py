from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.adjustment import (
    AdjustmentCreateRequest,
    AdjustmentResponse,
    AdjustmentUpdateRequest,
)
from app.api.schemas.common import OKResponse
from app.auth.dependencies import require_room_access
from app.database import get_db
from app.services.registry import get_adjustment_service, get_room_service

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import AuthContext
    from app.services.adjustment_service import AdjustmentService
    from app.services.room_service import RoomService

router = APIRouter(prefix="/api/rooms/{room_id}/adjustments", tags=["adjustments"], responses=ERROR_RESPONSES)


async def _receipt_id_for_room(db: AsyncSession, room_id: UUID, service: RoomService) -> UUID:
    receipt = await service.get_receipt(db, room_id)
    receipt_id = receipt.id
    await db.rollback()
    return receipt_id


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add adjustment",
    description="Create a tax, fee, discount, or manual adjustment through the service layer.",
    response_model=AdjustmentResponse,
)
async def add_adjustment(
    room_id: UUID,
    payload: AdjustmentCreateRequest,
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    adjustment_service: AdjustmentService = Depends(get_adjustment_service),
    room_service: RoomService = Depends(get_room_service),
) -> AdjustmentResponse:
    receipt_id = await _receipt_id_for_room(db, room_id, room_service)
    adjustment = await adjustment_service.add_adjustment(
        db,
        room_id=room_id,
        receipt_id=receipt_id,
        actor_id=ctx.participant_id,
        adj_type=payload.type,
        label=payload.label,
        amount_paise=payload.amount_paise,
        allocation_method=payload.allocation_method,
        rate_basis_points=payload.rate_basis_points,
        sort_order=payload.sort_order,
    )
    return AdjustmentResponse.model_validate(adjustment)


@router.patch(
    "/{adjustment_id}",
    summary="Update adjustment",
    description="Update an adjustment using service-layer CAS validation.",
    response_model=OKResponse,
)
async def update_adjustment(
    room_id: UUID,
    adjustment_id: UUID,
    payload: AdjustmentUpdateRequest,
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    adjustment_service: AdjustmentService = Depends(get_adjustment_service),
    room_service: RoomService = Depends(get_room_service),
) -> OKResponse:
    receipt_id = await _receipt_id_for_room(db, room_id, room_service)
    changes: dict[str, Any] = payload.model_dump(exclude={"version"}, exclude_none=True)
    await adjustment_service.update_adjustment(
        db,
        adjustment_id=adjustment_id,
        room_id=room_id,
        receipt_id=receipt_id,
        expected_version=payload.version,
        actor_id=ctx.participant_id,
        changes=changes,
    )
    return OKResponse()


@router.delete(
    "/{adjustment_id}",
    summary="Delete adjustment",
    description="Soft-delete an adjustment using service-layer CAS validation.",
    response_model=OKResponse,
)
async def delete_adjustment(
    room_id: UUID,
    adjustment_id: UUID,
    version: int = Query(ge=1),
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    adjustment_service: AdjustmentService = Depends(get_adjustment_service),
    room_service: RoomService = Depends(get_room_service),
) -> OKResponse:
    receipt_id = await _receipt_id_for_room(db, room_id, room_service)
    await adjustment_service.delete_adjustment(
        db,
        adjustment_id=adjustment_id,
        room_id=room_id,
        receipt_id=receipt_id,
        expected_version=version,
        actor_id=ctx.participant_id,
    )
    return OKResponse()
