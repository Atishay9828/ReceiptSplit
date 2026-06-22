from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.api.schemas.common import ORMModel

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class AdjustmentCreateRequest(BaseModel):
    type: str = Field(pattern="^(tax|service_charge|delivery_fee|discount|adjustment)$")
    label: str = Field(min_length=1, max_length=100)
    amount_paise: int = Field(gt=-10_000_000, le=10_000_000)
    allocation_method: str = Field(default="proportional", pattern="^(proportional|equal)$")
    rate_basis_points: int | None = Field(default=None, ge=0)
    sort_order: int = 0


class AdjustmentUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    label: str | None = Field(default=None, min_length=1, max_length=100)
    amount_paise: int | None = Field(default=None, gt=-10_000_000, le=10_000_000)
    allocation_method: str | None = Field(default=None, pattern="^(proportional|equal)$")
    rate_basis_points: int | None = Field(default=None, ge=0)


class AdjustmentResponse(ORMModel):
    id: UUID
    room_id: UUID
    type: str
    label: str
    amount_paise: int
    rate_basis_points: int | None
    allocation_method: str
    sort_order: int
    version: int
    created_at: datetime
