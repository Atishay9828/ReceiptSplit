from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    receipt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    allocation_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="individual"
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default="manual")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("quantity >= 1 AND quantity <= 999", name="ck_items_qty"),
        CheckConstraint("total_paise >= 0 AND total_paise <= 10000000", name="ck_items_total"),
        CheckConstraint(
            "allocation_mode IN ('individual','equal')", name="ck_items_allocation_mode"
        ),
        CheckConstraint("source IN ('manual','ocr')", name="ck_items_source"),
        CheckConstraint("version >= 1", name="ck_items_version"),
        Index(
            "idx_items_receipt",
            "receipt_id",
            "sort_order",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
