"""M013 security audit and abuse report tables.

Revision ID: 005_m013_security_hardening
Revises: 004_m012_settlement_mvp
Create Date: 2026-07-08
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "005_m013_security_hardening"
down_revision: str | None = "004_m012_settlement_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(length=30), server_default="unknown", nullable=False),
        sa.Column("ip_fingerprint", sa.String(length=32), nullable=True),
        sa.Column("user_agent", sa.String(length=200), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_participant_id"], ["room_participants.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["room_participants.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_logs_room_created", "audit_logs", ["room_id", "created_at"])
    op.create_index("idx_audit_logs_action_created", "audit_logs", ["action", "created_at"])

    op.create_table(
        "abuse_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reporter_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reporter_role", sa.String(length=30), server_default="unknown", nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "reason IN ('spam','fraud_suspected','wrong_payee','harassment','other')",
            name="ck_abuse_reports_reason",
        ),
        sa.ForeignKeyConstraint(["reporter_participant_id"], ["room_participants.id"]),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_abuse_reports_room_created", "abuse_reports", ["room_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_abuse_reports_room_created", table_name="abuse_reports")
    op.drop_table("abuse_reports")
    op.drop_index("idx_audit_logs_action_created", table_name="audit_logs")
    op.drop_index("idx_audit_logs_room_created", table_name="audit_logs")
    op.drop_table("audit_logs")
