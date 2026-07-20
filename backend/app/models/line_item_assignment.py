from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

if True:
    pass


class LineItemAssignment(Base):
    __tablename__ = "line_item_assignments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    room_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    line_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("line_items.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("room_participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    claimed_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("claimed_qty >= 1", name="ck_assign_qty"),
        UniqueConstraint("line_item_id", "participant_id", name="uq_assign_item_participant"),
        Index("idx_assign_room", "room_id"),
        Index("idx_assign_item", "line_item_id"),
        Index("idx_assign_participant", "participant_id"),
    )
