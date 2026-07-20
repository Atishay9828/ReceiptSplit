"""M011 OCR MVP tables.

Revision ID: 003_m011_ocr_mvp
Revises: 002_m008_auth_users
Create Date: 2026-07-03
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "003_m011_ocr_mvp"
down_revision: str | None = "002_m008_auth_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "receipt_images",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_table(
        "ocr_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','processing','succeeded','failed')", name="ck_ocr_jobs_status"
        ),
        sa.ForeignKeyConstraint(["image_id"], ["receipt_images.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ocr_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("redacted_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "provider_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["job_id"], ["ocr_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "parsed_receipts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ocr_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant_name", sa.String(length=200), nullable=True),
        sa.Column("subtotal_paise", sa.BigInteger(), nullable=True),
        sa.Column("tax_paise", sa.BigInteger(), nullable=True),
        sa.Column("discount_paise", sa.BigInteger(), nullable=True),
        sa.Column("total_paise", sa.BigInteger(), nullable=True),
        sa.Column(
            "items", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "adjustments",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("needs_review", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('draft','confirmed')", name="ck_parsed_receipts_status"),
        sa.ForeignKeyConstraint(["ocr_job_id"], ["ocr_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("parsed_receipts")
    op.drop_table("ocr_results")
    op.drop_table("ocr_jobs")
    op.drop_table("receipt_images")
