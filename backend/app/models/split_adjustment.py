from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
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

if True:
    pass


class SplitAdjustment(Base):
    __tablename__ = "split_adjustments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    room_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rate_basis_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allocation_method: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="proportional"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "type IN ('tax','service_charge','delivery_fee','discount','adjustment')",
            name="ck_adj_type",
        ),
        CheckConstraint(
            "amount_paise > -10000000 AND amount_paise <= 10000000", name="ck_adj_amount"
        ),
        CheckConstraint(
            "allocation_method IN ('proportional','equal')", name="ck_adj_alloc"
        ),
        CheckConstraint("version >= 1", name="ck_adj_version"),
        Index(
            "idx_adjustments_room",
            "room_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
