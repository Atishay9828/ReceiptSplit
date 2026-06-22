from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.api.schemas.common import ORMModel

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class ItemCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=999)
    total_paise: int = Field(ge=0, le=10_000_000)


class ItemUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: int | None = Field(default=None, ge=1, le=999)
    total_paise: int | None = Field(default=None, ge=0, le=10_000_000)


class ClaimItemRequest(BaseModel):
    item_version: int = Field(ge=1)
    claimed_qty: int = Field(ge=1)


class ItemResponse(ORMModel):
    id: UUID
    receipt_id: UUID
    name: str
    quantity: int
    total_paise: int
    source: str
    confidence: float
    sort_order: int
    version: int
    created_at: datetime


class ClaimResponse(ORMModel):
    id: UUID
    room_id: UUID
    line_item_id: UUID
    participant_id: UUID
    claimed_qty: int
    created_at: datetime
