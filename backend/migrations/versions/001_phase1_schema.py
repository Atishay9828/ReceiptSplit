"""
Phase 1 Schema — ReceiptSplit Foundation

Revision:  001
Branch:    head
Created:   2026-06-16

Tables created:
  rooms               — Bill room lifecycle state machine
  room_sequences      — Atomic per-room event sequence counters [Amendment DB-1]
  room_invites        — Capability tokens embedded in share links
  room_participants   — All participants including the creator
  receipts            — One receipt per room (Phase 1: manual entry)
  line_items          — Individual receipt line items
  split_adjustments   — Taxes, fees, discounts, adjustments [Amendment DB-4]
  line_item_assignments — Item claiming records
  split_sessions      — Computed split snapshots [Amendment DB-2, DB-5]
  participant_totals  — Per-participant breakdown
  room_events         — Append-only event log
  receipt_edits       — Item/adjustment edit audit trail [Amendment DB-3]

Design authorities:
  - Phase 1 Implementation Design §2.1
  - Phase 1 Design Amendments v1 (DB-1 through DB-5)
  - Product Decisions Document v2 §14 (constraints)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# ── Migration identifiers ─────────────────────────────────────────────────────
revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── rooms ─────────────────────────────────────────────────────────────────
    op.create_table(
        "rooms",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("split_mode", sa.String(20), nullable=False, server_default="equal"),
        sa.Column("payer_vpa", sa.String(50), nullable=True),
        sa.Column("payer_name", sa.String(100), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('draft','active','settling','settled','archived','expired')",
            name="ck_rooms_status",
        ),
        sa.CheckConstraint(
            "split_mode IN ('equal','item_wise')",
            name="ck_rooms_split_mode",
        ),
        sa.CheckConstraint("version >= 1", name="ck_rooms_version_positive"),
    )
    # Partial index for expiry cron: only scan non-terminal rooms
    op.create_index(
        "idx_rooms_status_expires",
        "rooms",
        ["status", "expires_at"],
        postgresql_where=sa.text("status NOT IN ('settled','archived','expired')"),
    )

    # ── room_sequences [Amendment DB-1] ───────────────────────────────────────
    # One row per room.  Used for atomic per-room event sequence generation.
    # next_seq is incremented via UPDATE ... RETURNING inside each business tx.
    op.create_table(
        "room_sequences",
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("next_seq", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("room_id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
    )

    # ── room_invites ──────────────────────────────────────────────────────────
    op.create_table(
        "room_invites",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="participant"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.CheckConstraint("type IN ('creator','participant')", name="ck_invites_type"),
        sa.UniqueConstraint("token_hash", name="uq_invites_token"),
    )
    op.create_index("idx_invites_room", "room_invites", ["room_id", "type"])

    # ── room_participants ─────────────────────────────────────────────────────
    op.create_table(
        "room_participants",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("invite_id", sa.UUID(), nullable=True),
        sa.Column("nickname", sa.String(30), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="participant"),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("left_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invite_id"], ["room_invites.id"]),
        sa.CheckConstraint("role IN ('creator','participant')", name="ck_participants_role"),
        sa.UniqueConstraint("token_hash", name="uq_participants_token"),
    )
    # Partial index: only index active participants (left_at IS NULL)
    op.create_index(
        "idx_participants_room",
        "room_participants",
        ["room_id"],
        postgresql_where=sa.text("left_at IS NULL"),
    )

    # ── receipts ──────────────────────────────────────────────────────────────
    op.create_table(
        "receipts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("is_replaceable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.CheckConstraint("source IN ('manual','ocr')", name="ck_receipts_source"),
        sa.UniqueConstraint("room_id", name="uq_receipts_room"),  # 1 receipt per room
    )

    # ── line_items ────────────────────────────────────────────────────────────
    op.create_table(
        "line_items",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_paise", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.CheckConstraint("quantity >= 1 AND quantity <= 999", name="ck_items_qty"),
        sa.CheckConstraint("total_paise >= 0 AND total_paise <= 10000000", name="ck_items_total"),
        sa.CheckConstraint("source IN ('manual','ocr')", name="ck_items_source"),
        sa.CheckConstraint("version >= 1", name="ck_items_version"),
    )
    op.create_index(
        "idx_items_receipt",
        "line_items",
        ["receipt_id", "sort_order"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── split_adjustments [Amendment DB-4] ────────────────────────────────────
    # amount_paise CHECK: signed range (not >= 0) — 'adjustment' type can be negative.
    # Non-negative enforcement for tax/fee/discount types is at the application layer.
    op.create_table(
        "split_adjustments",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("rate_basis_points", sa.Integer(), nullable=True),
        sa.Column(
            "allocation_method", sa.String(20), nullable=False, server_default="proportional"
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),  # Amendment DB-4
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "type IN ('tax','service_charge','delivery_fee','discount','adjustment')",
            name="ck_adj_type",
        ),
        # Signed range — 'adjustment' may be negative; others enforced at app layer
        sa.CheckConstraint(
            "amount_paise > -10000000 AND amount_paise <= 10000000",
            name="ck_adj_amount",
        ),
        sa.CheckConstraint(
            "allocation_method IN ('proportional','equal')",
            name="ck_adj_alloc",
        ),
        sa.CheckConstraint("version >= 1", name="ck_adj_version"),
    )
    op.create_index(
        "idx_adjustments_room",
        "split_adjustments",
        ["room_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── line_item_assignments ─────────────────────────────────────────────────
    op.create_table(
        "line_item_assignments",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("line_item_id", sa.UUID(), nullable=False),
        sa.Column("participant_id", sa.UUID(), nullable=False),
        sa.Column("claimed_qty", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["line_item_id"], ["line_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["room_participants.id"], ondelete="CASCADE"),
        sa.CheckConstraint("claimed_qty >= 1", name="ck_assign_qty"),
        sa.UniqueConstraint("line_item_id", "participant_id", name="uq_assign_item_participant"),
    )
    op.create_index("idx_assign_room", "line_item_assignments", ["room_id"])
    op.create_index("idx_assign_item", "line_item_assignments", ["line_item_id"])
    op.create_index("idx_assign_participant", "line_item_assignments", ["participant_id"])

    # ── split_sessions [Amendment DB-2, DB-5] ─────────────────────────────────
    # UNIQUE(room_id): enforces one-session-per-room invariant at DB level.
    # adjustments_snapshot: immutable JSON copy of adjustments at lock time.
    op.create_table(
        "split_sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("grand_total_paise", sa.BigInteger(), nullable=False),
        sa.Column("adjustments_snapshot", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.CheckConstraint("mode IN ('equal','item_wise')", name="ck_session_mode"),
        sa.UniqueConstraint("room_id", name="uq_session_room"),  # Amendment DB-2
    )

    # ── participant_totals ────────────────────────────────────────────────────
    op.create_table(
        "participant_totals",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("split_session_id", sa.UUID(), nullable=False),
        sa.Column("participant_id", sa.UUID(), nullable=False),
        sa.Column("items_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("discount_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tax_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("service_charge_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("delivery_fee_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("adjustment_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("is_payer", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["split_session_id"], ["split_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["room_participants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "split_session_id", "participant_id", name="uq_totals_session_participant"
        ),
    )
    op.create_index("idx_totals_session", "participant_totals", ["split_session_id"])

    # ── room_events ───────────────────────────────────────────────────────────
    # sequence_no is generated atomically via room_sequences (Amendment DB-1).
    op.create_table(
        "room_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("sequence_no", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
    )
    # UNIQUE on (room_id, sequence_no) — correctness guard for atomic sequence generator
    op.create_index(
        "idx_events_room_seq",
        "room_events",
        ["room_id", "sequence_no"],
        unique=True,
    )

    # ── receipt_edits [Amendment DB-3] ────────────────────────────────────────
    # Append-only audit trail for all creator edits to receipt contents.
    # Written in the same transaction as the mutation (TXN-2 pattern).
    op.create_table(
        "receipt_edits",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("participant_id", sa.UUID(), nullable=False),  # always the creator
        sa.Column("field", sa.String(100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["room_participants.id"]),
    )
    op.create_index("idx_receipt_edits_receipt", "receipt_edits", ["receipt_id", "created_at"])


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_table("receipt_edits")
    op.drop_table("room_events")
    op.drop_table("participant_totals")
    op.drop_table("split_sessions")
    op.drop_table("line_item_assignments")
    op.drop_table("split_adjustments")
    op.drop_table("line_items")
    op.drop_table("receipts")
    op.drop_table("room_participants")
    op.drop_table("room_invites")
    op.drop_table("room_sequences")
    op.drop_table("rooms")
