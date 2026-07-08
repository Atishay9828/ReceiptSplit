from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field

from app.api.schemas.common import ORMModel


class PayerDetailsRequest(BaseModel):
    payee_vpa: str = Field(min_length=3, max_length=80)
    payee_name: str = Field(min_length=1, max_length=80)


class DisputeSettlementRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class SettlementRequestResponse(ORMModel):
    id: UUID
    room_id: UUID
    participant_id: UUID
    amount_paise: int
    amount_display: str
    currency: str
    payee_vpa: str
    payee_name: str
    payment_reference: str
    status: str
    created_at: datetime
    updated_at: datetime
    opened_at: datetime | None
    claimed_paid_at: datetime | None
    payer_confirmed_at: datetime | None
    disputed_at: datetime | None


class SettlementAggregates(BaseModel):
    due_count: int
    payment_opened_count: int
    claimed_paid_count: int
    payer_confirmed_count: int
    disputed_count: int
    total_due_paise: int
    total_confirmed_paise: int


class SettlementSummaryResponse(BaseModel):
    room_id: UUID
    payer_details_configured: bool
    payee_vpa: str | None
    payee_name: str | None
    requests: list[SettlementRequestResponse]
    aggregates: SettlementAggregates


class OpenPaymentResponse(BaseModel):
    settlement_request_id: UUID
    status: str
    amount_paise: int
    amount_display: str
    payee_vpa: str
    payee_name: str
    payment_reference: str
    upi_uri: str
    qr_payload: str
    copy_vpa: str
    disclaimer: str

