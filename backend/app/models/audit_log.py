from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any
from uuid import UUID  # noqa: TC003

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    room_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True
    )
    participant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("room_participants.id"), nullable=True
    )
    actor_participant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("room_participants.id"), nullable=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(String(30), nullable=False, server_default="unknown")
    ip_fingerprint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_audit_logs_room_created", "room_id", "created_at"),
        Index("idx_audit_logs_action_created", "action", "created_at"),
    )
