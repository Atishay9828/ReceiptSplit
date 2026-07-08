from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from sqlalchemy import TIMESTAMP, BigInteger, CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class SettlementRequest(Base):
    __tablename__ = "settlement_requests"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    room_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    split_session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("split_sessions.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("room_participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    payee_vpa: Mapped[str] = mapped_column(String(80), nullable=False)
    payee_name: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_reference: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="due")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    opened_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    claimed_paid_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    payer_confirmed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    disputed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="1")

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_settlement_requests_amount_positive"),
        CheckConstraint("currency = 'INR'", name="ck_settlement_requests_currency_inr"),
        CheckConstraint(
            "status IN ('due','payment_opened','claimed_paid','payer_confirmed','disputed')",
            name="ck_settlement_requests_status",
        ),
        Index("idx_settlement_requests_room", "room_id"),
        Index("idx_settlement_requests_room_participant", "room_id", "participant_id"),
        Index("idx_settlement_requests_room_status", "room_id", "status"),
        Index(
            "uq_settlement_requests_room_participant_session",
            "room_id",
            "participant_id",
            "split_session_id",
            unique=True,
        ),
    )

