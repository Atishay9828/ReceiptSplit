from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from pydantic import ValidationError

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.ocr import (
    BrowserOcrCandidateRequest,
    OcrJobResponse,
    ParsedReceiptConfirmResponse,
    ParsedReceiptDraftResponse,
    ParsedReceiptDraftUpdateRequest,
    ReceiptUploadResponse,
    parsed_receipt_response_from_model,
)
from app.auth.dependencies import AuthorizedRoomActor, require_room_owner_or_creator
from app.config import settings
from app.database import get_db
from app.ocr.contracts import OcrProviderResult, ParsedReceiptDraft
from app.security.rate_limit import RateLimitRule, client_host, enforce_rate_limit
from app.services.registry import get_audit_service, get_ocr_service
from app.shared.errors import DomainError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.parsed_receipt import ParsedReceipt
    from app.ocr.service import ReceiptOcrService
    from app.services.audit_service import AuditService


router = APIRouter(prefix="/api/rooms/{room_id}", tags=["ocr"], responses=ERROR_RESPONSES)


@router.post(
    "/receipts/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=ReceiptUploadResponse,
    summary="Upload receipt image and create OCR draft",
)
async def upload_receipt_image(
    room_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    ocr_candidate: str | None = Form(default=None),
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: ReceiptOcrService = Depends(get_ocr_service),
    audit: AuditService = Depends(get_audit_service),
) -> ReceiptUploadResponse:
    enforce_rate_limit(
        request,
        action="ocr.upload",
        key_parts=[str(room_id), str(actor.actor_id), client_host(request)],
        rule=RateLimitRule(limit=20, window_seconds=3600),
    )
    candidate_result = _parse_browser_candidate(ocr_candidate)
    content = await file.read(settings.ocr_max_image_bytes + 1)
    job, parsed = await service.upload_and_process(
        db,
        room_id=room_id,
        actor_id=actor.actor_id,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        candidate_result=candidate_result,
    )
    await audit.record(
        db,
        action="receipt.uploaded",
        room_id=room_id,
        actor_participant_id=actor.participant.participant_id if actor.participant else None,
        actor_user_id=actor.user.id if actor.user else None,
        actor_type="creator",
        metadata={
            "content_type": file.content_type or "application/octet-stream",
            "ocr_source": candidate_result.provider if candidate_result else "server_provider",
        },
        request=request,
    )
    return ReceiptUploadResponse(
        receipt_id=job.receipt_id,
        image_id=job.image_id,
        job_id=job.id,
        status=job.status,
        parsed_receipt_id=parsed.id if parsed else None,
    )


@router.get(
    "/ocr-jobs/{job_id}",
    response_model=OcrJobResponse,
    summary="Get OCR job",
)
async def get_ocr_job(
    room_id: UUID,
    job_id: UUID,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: ReceiptOcrService = Depends(get_ocr_service),
) -> OcrJobResponse:
    job = await service.get_job(db, room_id, job_id)
    parsed = await _parsed_for_job(db, room_id, job.id, service)
    response = OcrJobResponse.model_validate(job)
    response.parsed_receipt_id = parsed.id if parsed else None
    return response


@router.get(
    "/parsed-receipts/{parsed_receipt_id}",
    response_model=ParsedReceiptDraftResponse,
    summary="Get parsed receipt draft",
)
async def get_parsed_receipt(
    room_id: UUID,
    parsed_receipt_id: UUID,
    include_raw_text: bool = Query(default=False),
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: ReceiptOcrService = Depends(get_ocr_service),
) -> ParsedReceiptDraftResponse:
    parsed = await service.get_parsed(db, room_id, parsed_receipt_id)
    redacted_raw = (
        await service.redacted_raw_text_for_parsed(db, parsed_receipt_id)
        if include_raw_text
        else None
    )
    return parsed_receipt_response_from_model(parsed, redacted_raw)


@router.patch(
    "/parsed-receipts/{parsed_receipt_id}",
    response_model=ParsedReceiptDraftResponse,
    summary="Update parsed receipt draft",
)
async def update_parsed_receipt(
    room_id: UUID,
    parsed_receipt_id: UUID,
    payload: ParsedReceiptDraftUpdateRequest,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: ReceiptOcrService = Depends(get_ocr_service),
) -> ParsedReceiptDraftResponse:
    current = await service.get_parsed(db, room_id, parsed_receipt_id)
    draft = ParsedReceiptDraft(
        merchant_name=payload.merchant_name
        if payload.merchant_name is not None
        else current.merchant_name,
        subtotal_paise=payload.subtotal_paise
        if payload.subtotal_paise is not None
        else current.subtotal_paise,
        tax_paise=payload.tax_paise if payload.tax_paise is not None else current.tax_paise,
        discount_paise=payload.discount_paise
        if payload.discount_paise is not None
        else current.discount_paise,
        total_paise=payload.total_paise
        if payload.total_paise is not None
        else current.total_paise,
        items=payload.items if payload.items is not None else current.items,
        adjustments=payload.adjustments
        if payload.adjustments is not None
        else current.adjustments,
        warnings=payload.warnings if payload.warnings is not None else current.warnings,
        confidence=current.confidence,
        needs_review=payload.needs_review
        if payload.needs_review is not None
        else current.needs_review,
        parser_version=current.parser_version,
    )
    parsed = await service.update_parsed(db, room_id, parsed_receipt_id, draft, actor.actor_id)
    return parsed_receipt_response_from_model(parsed)


@router.post(
    "/parsed-receipts/{parsed_receipt_id}/confirm",
    response_model=ParsedReceiptConfirmResponse,
    summary="Confirm parsed receipt into room items",
)
async def confirm_parsed_receipt(
    room_id: UUID,
    parsed_receipt_id: UUID,
    request: Request,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: ReceiptOcrService = Depends(get_ocr_service),
    audit: AuditService = Depends(get_audit_service),
) -> ParsedReceiptConfirmResponse:
    parsed, item_ids, adjustment_ids, already_confirmed, events = await service.confirm_parsed(
        db, room_id, parsed_receipt_id, actor.actor_id
    )
    await audit.record(
        db,
        action="ocr.confirmed",
        room_id=room_id,
        actor_participant_id=actor.participant.participant_id if actor.participant else None,
        actor_user_id=actor.user.id if actor.user else None,
        actor_type="creator",
        metadata={
            "parsed_receipt_id": str(parsed_receipt_id),
            "already_confirmed": already_confirmed,
        },
        request=request,
    )
    return ParsedReceiptConfirmResponse(
        parsed_receipt_id=parsed.id,
        status=parsed.status,
        already_confirmed=already_confirmed,
        created_item_ids=item_ids,
        created_adjustment_ids=adjustment_ids,
        events=events,
    )


async def _parsed_for_job(
    db: AsyncSession, room_id: UUID, job_id: UUID, service: ReceiptOcrService
) -> ParsedReceipt | None:
    from sqlalchemy import select

    from app.models.parsed_receipt import ParsedReceipt

    result = await db.execute(
        select(ParsedReceipt).where(
            ParsedReceipt.room_id == room_id,
            ParsedReceipt.ocr_job_id == job_id,
        )
    )
    return result.scalars().first()


def _parse_browser_candidate(value: str | None) -> OcrProviderResult | None:
    if value is None:
        return None
    if len(value) > 120_000:
        raise DomainError(
            code="INVALID_OCR_CANDIDATE",
            message="Browser OCR candidate is too large.",
        )
    try:
        candidate = BrowserOcrCandidateRequest.model_validate_json(value)
    except ValidationError:
        raise DomainError(
            code="INVALID_OCR_CANDIDATE",
            message="Browser OCR candidate is invalid.",
        ) from None
    return candidate.to_provider_result()
