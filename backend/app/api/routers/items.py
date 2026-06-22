from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.common import OKResponse
from app.api.schemas.item import (
    ClaimItemRequest,
    ClaimResponse,
    ItemCreateRequest,
    ItemResponse,
    ItemUpdateRequest,
)
from app.auth.dependencies import require_room_access
from app.database import get_db
from app.services.registry import get_item_service, get_room_service

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import AuthContext
    from app.services.item_service import ItemService
    from app.services.room_service import RoomService

router = APIRouter(prefix="/api/rooms/{room_id}/items", tags=["items"], responses=ERROR_RESPONSES)


async def _receipt_id_for_room(db: AsyncSession, room_id: UUID, service: RoomService) -> UUID:
    receipt = await service.get_receipt(db, room_id)
    receipt_id = receipt.id
    await db.rollback()
    return receipt_id


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add item",
    description="Create a receipt line item through the item service.",
    response_model=ItemResponse,
)
async def add_item(
    room_id: UUID,
    payload: ItemCreateRequest,
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    item_service: ItemService = Depends(get_item_service),
    room_service: RoomService = Depends(get_room_service),
) -> ItemResponse:
    receipt_id = await _receipt_id_for_room(db, room_id, room_service)
    item = await item_service.add_item(
        db,
        receipt_id=receipt_id,
        room_id=room_id,
        actor_id=ctx.participant_id,
        name=payload.name,
        quantity=payload.quantity,
        total_paise=payload.total_paise,
    )
    return ItemResponse.model_validate(item)


@router.patch(
    "/{item_id}",
    summary="Update item",
    description="Update a line item using service-layer CAS validation.",
    response_model=OKResponse,
)
async def update_item(
    room_id: UUID,
    item_id: UUID,
    payload: ItemUpdateRequest,
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    item_service: ItemService = Depends(get_item_service),
    room_service: RoomService = Depends(get_room_service),
) -> OKResponse:
    receipt_id = await _receipt_id_for_room(db, room_id, room_service)
    changes: dict[str, Any] = payload.model_dump(exclude={"version"}, exclude_none=True)
    await item_service.update_item(
        db,
        item_id=item_id,
        room_id=room_id,
        receipt_id=receipt_id,
        expected_version=payload.version,
        actor_id=ctx.participant_id,
        changes=changes,
    )
    return OKResponse()


@router.delete(
    "/{item_id}",
    summary="Delete item",
    description="Soft-delete a line item using service-layer CAS validation.",
    response_model=OKResponse,
)
async def delete_item(
    room_id: UUID,
    item_id: UUID,
    version: int = Query(ge=1),
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    item_service: ItemService = Depends(get_item_service),
    room_service: RoomService = Depends(get_room_service),
) -> OKResponse:
    receipt_id = await _receipt_id_for_room(db, room_id, room_service)
    await item_service.delete_item(
        db,
        item_id=item_id,
        room_id=room_id,
        receipt_id=receipt_id,
        expected_version=version,
        actor_id=ctx.participant_id,
    )
    return OKResponse()


@router.post(
    "/{item_id}/claim",
    status_code=status.HTTP_201_CREATED,
    summary="Claim item",
    description="Claim units of a line item for the authenticated participant.",
    response_model=ClaimResponse,
)
async def claim_item(
    room_id: UUID,
    item_id: UUID,
    payload: ClaimItemRequest,
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    service: ItemService = Depends(get_item_service),
) -> ClaimResponse:
    assignment = await service.claim_item(
        db,
        room_id=room_id,
        item_id=item_id,
        item_version=payload.item_version,
        participant_id=ctx.participant_id,
        claimed_qty=payload.claimed_qty,
    )
    return ClaimResponse.model_validate(assignment)


@router.delete(
    "/{item_id}/claim",
    summary="Unclaim item",
    description="Remove the authenticated participant's claim from a line item.",
    response_model=OKResponse,
)
async def unclaim_item(
    room_id: UUID,
    item_id: UUID,
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    service: ItemService = Depends(get_item_service),
) -> OKResponse:
    await service.unclaim_item(db, room_id=room_id, item_id=item_id, participant_id=ctx.participant_id)
    return OKResponse()
