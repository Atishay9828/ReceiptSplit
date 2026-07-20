from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class OcrJob(Base):
    __tablename__ = "ocr_jobs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    room_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    receipt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    image_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receipt_images.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','processing','succeeded','failed')", name="ck_ocr_jobs_status"
        ),
    )
