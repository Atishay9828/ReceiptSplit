from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Literal
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field

AbuseReason = Literal["spam", "fraud_suspected", "wrong_payee", "harassment", "other"]


class AbuseReportRequest(BaseModel):
    reason: AbuseReason
    message: str | None = Field(default=None, max_length=500)


class AbuseReportResponse(BaseModel):
    id: UUID
    room_id: UUID
    reason: AbuseReason
    message: str | None
    created_at: datetime
