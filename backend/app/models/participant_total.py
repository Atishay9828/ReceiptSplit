from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

if TYPE_CHECKING:
    from uuid import UUID


class ParticipantTotal(Base):
    __tablename__ = "participant_totals"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    split_session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("split_sessions.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("room_participants.id", ondelete="CASCADE"), nullable=False
    )
    items_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    discount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    tax_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    service_charge_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    delivery_fee_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    adjustment_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    is_payer: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        UniqueConstraint(
            "split_session_id", "participant_id", name="uq_totals_session_participant"
        ),
        Index("idx_totals_session", "split_session_id"),
    )
