from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any
from uuid import UUID  # noqa: TC003

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ParsedReceipt(Base):
    __tablename__ = "parsed_receipts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    room_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    receipt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    ocr_job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ocr_jobs.id", ondelete="CASCADE"), nullable=False
    )
    merchant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subtotal_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tax_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    discount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default="[]")
    adjustments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('draft','confirmed')", name="ck_parsed_receipts_status"),
    )
