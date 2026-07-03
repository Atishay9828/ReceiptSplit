from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field

from app.api.schemas.common import ORMModel
from app.ocr.contracts import ParsedReceiptAdjustment, ParsedReceiptLine


class ReceiptUploadResponse(BaseModel):
    receipt_id: UUID
    image_id: UUID
    job_id: UUID
    status: str
    parsed_receipt_id: UUID | None = None


class OcrJobResponse(ORMModel):
    id: UUID
    room_id: UUID
    receipt_id: UUID
    image_id: UUID
    provider: str
    status: str
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    parsed_receipt_id: UUID | None = None


class ParsedReceiptDraftResponse(ORMModel):
    id: UUID
    room_id: UUID
    receipt_id: UUID
    ocr_job_id: UUID
    merchant_name: str | None
    subtotal_paise: int | None
    tax_paise: int | None
    discount_paise: int | None
    total_paise: int | None
    items: list[ParsedReceiptLine]
    adjustments: list[ParsedReceiptAdjustment]
    warnings: list[str]
    confidence: float
    needs_review: bool
    parser_version: str
    status: str
    redacted_raw_text: str | None = None


class ParsedReceiptDraftUpdateRequest(BaseModel):
    merchant_name: str | None = Field(default=None, max_length=200)
    subtotal_paise: int | None = Field(default=None, ge=0)
    tax_paise: int | None = Field(default=None, ge=0)
    discount_paise: int | None = None
    total_paise: int | None = Field(default=None, ge=0)
    items: list[ParsedReceiptLine] | None = None
    adjustments: list[ParsedReceiptAdjustment] | None = None
    warnings: list[str] | None = None
    needs_review: bool | None = None


class ParsedReceiptConfirmResponse(BaseModel):
    parsed_receipt_id: UUID
    status: str
    already_confirmed: bool
    created_item_ids: list[UUID]
    created_adjustment_ids: list[UUID]
    events: list[str]


def parsed_receipt_response_from_model(
    parsed: Any, redacted_raw_text: str | None = None
) -> ParsedReceiptDraftResponse:
    return ParsedReceiptDraftResponse(
        id=parsed.id,
        room_id=parsed.room_id,
        receipt_id=parsed.receipt_id,
        ocr_job_id=parsed.ocr_job_id,
        merchant_name=parsed.merchant_name,
        subtotal_paise=parsed.subtotal_paise,
        tax_paise=parsed.tax_paise,
        discount_paise=parsed.discount_paise,
        total_paise=parsed.total_paise,
        items=[ParsedReceiptLine.model_validate(item) for item in parsed.items],
        adjustments=[ParsedReceiptAdjustment.model_validate(adj) for adj in parsed.adjustments],
        warnings=list(parsed.warnings),
        confidence=parsed.confidence,
        needs_review=parsed.needs_review,
        parser_version=parsed.parser_version,
        status=parsed.status,
        redacted_raw_text=redacted_raw_text,
    )
