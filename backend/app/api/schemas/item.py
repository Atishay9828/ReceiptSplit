from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.common import ORMModel
from app.shared.validators import strip_html

if True:
    pass


class ItemCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=999)
    total_paise: int = Field(ge=0, le=10_000_000)

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        if isinstance(v, str):
            return strip_html(v)
        return v


class ItemUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: int | None = Field(default=None, ge=1, le=999)
    total_paise: int | None = Field(default=None, ge=0, le=10_000_000)

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return strip_html(v)
        return v


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
