from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.line_item import LineItem
from app.models.ocr_job import OcrJob
from app.models.ocr_result import OcrResult
from app.models.parsed_receipt import ParsedReceipt
from app.models.receipt_image import ReceiptImage
from app.models.split_adjustment import SplitAdjustment
from app.ocr.contracts import OcrImageInput, OcrProviderResult, ParsedReceiptDraft
from app.ocr.errors import OcrJobNotFound, ParsedReceiptNotFound
from app.ocr.redaction import redact_sensitive_ocr_text
from app.shared.errors import DomainError, RoomNotFound

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.ocr.contracts import ImagePreprocessor, OcrProvider, ReceiptParser
    from app.ocr.storage import ReceiptImageStorage
    from app.ocr.validation import ReceiptImageValidator
    from app.repositories.postgres.receipt import PostgresReceiptRepository
    from app.repositories.postgres.room import PostgresRoomRepository
    from app.services.event_publisher import EventPublisher


class ReceiptOcrService:
    def __init__(
        self,
        room_repo: PostgresRoomRepository,
        receipt_repo: PostgresReceiptRepository,
        validator: ReceiptImageValidator,
        preprocessor: ImagePreprocessor,
        storage: ReceiptImageStorage,
        provider: OcrProvider,
        parser: ReceiptParser,
        event_publisher: EventPublisher,
        store_raw_text: bool,
    ) -> None:
        self._room_repo = room_repo
        self._receipt_repo = receipt_repo
        self._validator = validator
        self._preprocessor = preprocessor
        self._storage = storage
        self._provider = provider
        self._parser = parser
        self._events = event_publisher
        self._store_raw_text = store_raw_text

    async def upload_and_process(
        self,
        db: AsyncSession,
        room_id: UUID,
        actor_id: UUID,
        content: bytes,
        content_type: str,
        candidate_result: OcrProviderResult | None = None,
    ) -> tuple[OcrJob, ParsedReceipt | None]:
        room = await self._room_repo.get_by_id(db, room_id)
        if room is None:
            raise RoomNotFound()
        receipt = await self._receipt_repo.get_by_room(db, room_id)
        if receipt is None:
            raise DomainError(code="RECEIPT_NOT_FOUND", message="Receipt not found.")

        validated = self._validator.validate(content, content_type)
        preprocessed = await self._preprocessor.preprocess(content, validated.content_type)
        stored = await self._storage.save(preprocessed.content, preprocessed.content_type)

        image = ReceiptImage(
            room_id=room_id,
            receipt_id=receipt.id,
            storage_key=stored.storage_key,
            content_type=preprocessed.content_type,
            byte_size=stored.byte_size,
            width=preprocessed.width,
            height=preprocessed.height,
            sha256=validated.sha256,
        )
        db.add(image)
        await db.flush()

        provider_name = (
            candidate_result.provider
            if candidate_result is not None
            else self._provider.__class__.__name__.removesuffix("OcrProvider").lower()
        )
        job = OcrJob(
            room_id=room_id,
            receipt_id=receipt.id,
            image_id=image.id,
            provider=provider_name,
            status="processing",
        )
        db.add(job)
        await db.flush()

        try:
            result = candidate_result
            if result is None:
                result = await self._provider.extract_text(
                    OcrImageInput(
                        content=preprocessed.content,
                        content_type=preprocessed.content_type,
                        width=preprocessed.width,
                        height=preprocessed.height,
                    )
                )
            parsed_draft = self._parser.parse(result.raw_text)
        except DomainError as exc:
            job.status = "failed"
            job.error_code = exc.code
            job.error_message = exc.message[:300]
            job.completed_at = datetime.now(UTC)
            await db.flush()
            return job, None

        redacted = redact_sensitive_ocr_text(result.raw_text)
        ocr_result = OcrResult(
            job_id=job.id,
            receipt_id=receipt.id,
            provider=result.provider,
            raw_text=result.raw_text if self._store_raw_text else None,
            redacted_text=redacted,
            confidence=result.confidence,
            provider_metadata=result.provider_metadata,
        )
        db.add(ocr_result)

        parsed = self._parsed_model_from_draft(room_id, receipt.id, job.id, parsed_draft)
        db.add(parsed)
        job.status = "succeeded"
        job.completed_at = datetime.now(UTC)
        await db.flush()

        await self._events.append_in_tx(
            db,
            room_id,
            "ocr.draft_created",
            actor_id,
            {"job_id": str(job.id), "parsed_receipt_id": str(parsed.id)},
        )
        return job, parsed

    async def get_job(self, db: AsyncSession, room_id: UUID, job_id: UUID) -> OcrJob:
        result = await db.execute(
            select(OcrJob).where(OcrJob.id == job_id, OcrJob.room_id == room_id)
        )
        job = result.scalars().first()
        if job is None:
            raise OcrJobNotFound()
        return job

    async def get_parsed(
        self, db: AsyncSession, room_id: UUID, parsed_receipt_id: UUID
    ) -> ParsedReceipt:
        result = await db.execute(
            select(ParsedReceipt).where(
                ParsedReceipt.id == parsed_receipt_id,
                ParsedReceipt.room_id == room_id,
            )
        )
        parsed = result.scalars().first()
        if parsed is None:
            raise ParsedReceiptNotFound()
        return parsed

    async def redacted_raw_text_for_parsed(
        self, db: AsyncSession, parsed_receipt_id: UUID
    ) -> str | None:
        result = await db.execute(
            select(OcrResult.redacted_text)
            .join(OcrJob, OcrJob.id == OcrResult.job_id)
            .join(ParsedReceipt, ParsedReceipt.ocr_job_id == OcrJob.id)
            .where(ParsedReceipt.id == parsed_receipt_id)
        )
        return result.scalars().first()

    async def update_parsed(
        self,
        db: AsyncSession,
        room_id: UUID,
        parsed_receipt_id: UUID,
        draft: ParsedReceiptDraft,
        actor_id: UUID,
    ) -> ParsedReceipt:
        parsed = await self.get_parsed(db, room_id, parsed_receipt_id)
        if parsed.status == "confirmed":
            raise DomainError(
                code="OCR_DRAFT_CONFIRMED", message="OCR draft is already confirmed."
            )
        parsed.merchant_name = draft.merchant_name
        parsed.subtotal_paise = draft.subtotal_paise
        parsed.tax_paise = draft.tax_paise
        parsed.discount_paise = draft.discount_paise
        parsed.total_paise = draft.total_paise
        parsed.items = [item.model_dump() for item in draft.items]
        parsed.adjustments = [adjustment.model_dump() for adjustment in draft.adjustments]
        parsed.warnings = draft.warnings
        parsed.confidence = draft.confidence
        parsed.needs_review = draft.needs_review
        await db.flush()
        await self._events.append_in_tx(
            db,
            room_id,
            "ocr.draft_updated",
            actor_id,
            {"parsed_receipt_id": str(parsed.id)},
        )
        return parsed

    async def confirm_parsed(
        self,
        db: AsyncSession,
        room_id: UUID,
        parsed_receipt_id: UUID,
        actor_id: UUID,
    ) -> tuple[ParsedReceipt, list[UUID], list[UUID], bool, list[str]]:
        parsed = await self.get_parsed(db, room_id, parsed_receipt_id)
        if parsed.status == "confirmed":
            return parsed, [], [], True, []
        if not parsed.items:
            raise DomainError(
                code="NO_ITEMS", message="Add at least one item before confirming OCR."
            )

        created_item_ids: list[UUID] = []
        created_adjustment_ids: list[UUID] = []
        event_types: list[str] = []
        for sort_order, item_data in enumerate(parsed.items):
            item = LineItem(
                receipt_id=parsed.receipt_id,
                name=str(item_data["name"]),
                quantity=int(item_data["quantity"]),
                total_paise=int(item_data["total_paise"]),
                source="ocr",
                confidence=float(item_data.get("confidence", parsed.confidence)),
                sort_order=sort_order,
            )
            db.add(item)
            await db.flush()
            created_item_ids.append(item.id)
            event_types.append("item.created")
            await self._events.append_in_tx(
                db,
                room_id,
                "item.created",
                actor_id,
                {"item_id": str(item.id), "name": item.name, "source": "ocr"},
            )

        for sort_order, adj_data in enumerate(parsed.adjustments):
            adjustment = SplitAdjustment(
                room_id=room_id,
                type=str(adj_data["type"]),
                label=str(adj_data["label"]),
                amount_paise=int(adj_data["amount_paise"]),
                allocation_method=str(adj_data.get("allocation_method", "proportional")),
                sort_order=sort_order,
            )
            db.add(adjustment)
            await db.flush()
            created_adjustment_ids.append(adjustment.id)
            event_types.append("adjustment.created")
            await self._events.append_in_tx(
                db,
                room_id,
                "adjustment.created",
                actor_id,
                {"adjustment_id": str(adjustment.id), "type": adjustment.type, "source": "ocr"},
            )

        parsed.status = "confirmed"
        parsed.confirmed_at = datetime.now(UTC)
        await self._events.append_in_tx(
            db,
            room_id,
            "room.updated",
            actor_id,
            {"source": "ocr_confirmed", "parsed_receipt_id": str(parsed.id)},
        )
        event_types.append("room.updated")
        await db.flush()
        return parsed, created_item_ids, created_adjustment_ids, False, event_types

    def _parsed_model_from_draft(
        self, room_id: UUID, receipt_id: UUID, job_id: UUID, draft: ParsedReceiptDraft
    ) -> ParsedReceipt:
        return ParsedReceipt(
            room_id=room_id,
            receipt_id=receipt_id,
            ocr_job_id=job_id,
            merchant_name=draft.merchant_name,
            subtotal_paise=draft.subtotal_paise,
            tax_paise=draft.tax_paise,
            discount_paise=draft.discount_paise,
            total_paise=draft.total_paise,
            items=[item.model_dump() for item in draft.items],
            adjustments=[adjustment.model_dump() for adjustment in draft.adjustments],
            warnings=draft.warnings,
            confidence=draft.confidence,
            needs_review=draft.needs_review,
            parser_version=draft.parser_version,
        )
