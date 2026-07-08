"""M012 UPI settlement MVP tables.

Revision ID: 004_m012_settlement_mvp
Revises: 003_m011_ocr_mvp
Create Date: 2026-07-06
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "004_m012_settlement_mvp"
down_revision: str | None = "003_m011_ocr_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "settlement_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("split_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("payee_vpa", sa.String(length=80), nullable=False),
        sa.Column("payee_name", sa.String(length=100), nullable=False),
        sa.Column("payment_reference", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="due", nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("claimed_paid_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("payer_confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("disputed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.CheckConstraint("amount_paise > 0", name="ck_settlement_requests_amount_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_settlement_requests_currency_inr"),
        sa.CheckConstraint(
            "status IN ('due','payment_opened','claimed_paid','payer_confirmed','disputed')",
            name="ck_settlement_requests_status",
        ),
        sa.ForeignKeyConstraint(["participant_id"], ["room_participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["split_session_id"], ["split_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_reference"),
    )
    op.create_index("idx_settlement_requests_room", "settlement_requests", ["room_id"])
    op.create_index(
        "idx_settlement_requests_room_participant",
        "settlement_requests",
        ["room_id", "participant_id"],
    )
    op.create_index(
        "idx_settlement_requests_room_status",
        "settlement_requests",
        ["room_id", "status"],
    )
    op.create_index(
        "uq_settlement_requests_room_participant_session",
        "settlement_requests",
        ["room_id", "participant_id", "split_session_id"],
        unique=True,
    )

    op.create_table(
        "settlement_status_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("settlement_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["actor_participant_id"], ["room_participants.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["room_participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["settlement_request_id"], ["settlement_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_settlement_status_events_room_request_created",
        "settlement_status_events",
        ["room_id", "settlement_request_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_settlement_status_events_room_request_created",
        table_name="settlement_status_events",
    )
    op.drop_table("settlement_status_events")
    op.drop_index(
        "uq_settlement_requests_room_participant_session", table_name="settlement_requests"
    )
    op.drop_index("idx_settlement_requests_room_status", table_name="settlement_requests")
    op.drop_index("idx_settlement_requests_room_participant", table_name="settlement_requests")
    op.drop_index("idx_settlement_requests_room", table_name="settlement_requests")
    op.drop_table("settlement_requests")
