from __future__ import annotations
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class RoomParticipant(Base):
    __tablename__ = "room_participants"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    room_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    invite_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("room_invites.id"), nullable=True
    )
    nickname: Mapped[str] = mapped_column(String(30), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="participant")
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    left_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('creator','participant')", name="ck_participants_role"),
        Index(
            "idx_participants_room",
            "room_id",
            postgresql_where=text("left_at IS NULL"),
        ),
    )
