from __future__ import annotations
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RoomSequence(Base):
    __tablename__ = "room_sequences"

    room_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True
    )
    next_seq: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
