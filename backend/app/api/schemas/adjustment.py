from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.schemas.common import ORMModel
from app.domain.adjustments import ADJUSTMENT_TYPES, is_percentage_allowed
from app.shared.validators import strip_html

if True:
    pass


class AdjustmentCreateRequest(BaseModel):
    type: str = Field(pattern="^(tax|service_charge|delivery_fee|packaging_fee|tip|discount|coupon|offer|adjustment|rounding)$")
    label: str = Field(min_length=1, max_length=100)
    amount_paise: int = Field(default=0, gt=-10_000_000, le=10_000_000)
    allocation_method: str = Field(default="proportional", pattern="^(proportional|equal)$")
    rate_basis_points: int | None = Field(default=None, gt=0, le=10_000)
    sort_order: int = 0

    @field_validator("label", mode="before")
    @classmethod
    def sanitize_label(cls, v: str) -> str:
        if isinstance(v, str):
            return strip_html(v)
        return v

    @model_validator(mode="after")
    def validate_value_mode(self) -> AdjustmentCreateRequest:
        if self.type not in ADJUSTMENT_TYPES:
            raise ValueError("Unsupported adjustment type.")
        if self.rate_basis_points is not None:
            if not is_percentage_allowed(self.type):
                raise ValueError("Rounding adjustments must use a flat amount.")
            return self
        if self.amount_paise == 0:
            raise ValueError("Flat adjustments require a non-zero amount.")
        return self


class AdjustmentUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    label: str | None = Field(default=None, min_length=1, max_length=100)
    amount_paise: int | None = Field(default=None, gt=-10_000_000, le=10_000_000)
    allocation_method: str | None = Field(default=None, pattern="^(proportional|equal)$")
    rate_basis_points: int | None = Field(default=None, gt=0, le=10_000)

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
