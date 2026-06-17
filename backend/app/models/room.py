from __future__ import annotations
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    split_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default="equal")
    payer_vpa: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','settling','settled','archived','expired')",
            name="ck_rooms_status",
        ),
        CheckConstraint("split_mode IN ('equal','item_wise')", name="ck_rooms_split_mode"),
        CheckConstraint("version >= 1", name="ck_rooms_version_positive"),
        Index(
            "idx_rooms_status_expires",
            "status",
            "expires_at",
            postgresql_where=text("status NOT IN ('settled','archived','expired')"),
        ),
    )
