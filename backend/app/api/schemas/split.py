from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.api.schemas.common import ORMModel

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class VersionedRequest(BaseModel):
    version: int = Field(ge=1)


class ParticipantTotalResponse(ORMModel):
    participant_id: UUID
    items_paise: int
    discount_paise: int
    tax_paise: int
    service_charge_paise: int
    delivery_fee_paise: int
    adjustment_paise: int
    total_paise: int
    is_payer: bool


class SplitPreviewResponse(BaseModel):
    grand_total_paise: int
    participant_totals: list[ParticipantTotalResponse]


class SplitSessionResponse(ORMModel):
    id: UUID
    room_id: UUID
    mode: str
    grand_total_paise: int
    adjustments_snapshot: list[dict[str, Any]]
    is_locked: bool
    computed_at: datetime
    version: int


class CurrentSplitSessionResponse(BaseModel):
    session: SplitSessionResponse | None
