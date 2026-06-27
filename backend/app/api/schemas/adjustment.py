from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.common import ORMModel
from app.shared.validators import strip_html

if True:
    pass


class AdjustmentCreateRequest(BaseModel):
    type: str = Field(pattern="^(tax|service_charge|delivery_fee|discount|adjustment)$")
    label: str = Field(min_length=1, max_length=100)
    amount_paise: int = Field(gt=-10_000_000, le=10_000_000)
    allocation_method: str = Field(default="proportional", pattern="^(proportional|equal)$")
    rate_basis_points: int | None = Field(default=None, ge=0)
    sort_order: int = 0

    @field_validator("label", mode="before")
    @classmethod
    def sanitize_label(cls, v: str) -> str:
        if isinstance(v, str):
            return strip_html(v)
        return v


class AdjustmentUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    label: str | None = Field(default=None, min_length=1, max_length=100)
    amount_paise: int | None = Field(default=None, gt=-10_000_000, le=10_000_000)
    allocation_method: str | None = Field(default=None, pattern="^(proportional|equal)$")
    rate_basis_points: int | None = Field(default=None, ge=0)

    @field_validator("label", mode="before")
    @classmethod
    def sanitize_label(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return strip_html(v)
        return v


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
