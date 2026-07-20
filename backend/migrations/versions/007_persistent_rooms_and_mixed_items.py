"""Add per-item allocation mode and persistent room foundations.

Revision ID: 007_persistent_rooms
Revises: 006_m0151_adjustment_types
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "007_persistent_rooms"
down_revision: str | None = "006_m0151_adjustment_types"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.String(length=80), nullable=True))
    op.create_unique_constraint("uq_users_username", "users", ["username"])

    op.create_table(
        "groups",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("creator_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "group_members",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="member", nullable=False),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('owner','member')", name="ck_group_members_role"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_members_group_user"),
    )
    op.create_index("idx_group_members_user", "group_members", ["user_id", "joined_at"])
    op.create_table(
        "friendships",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_low_id", sa.UUID(), nullable=False),
        sa.Column("user_high_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("user_low_id < user_high_id", name="ck_friendships_canonical_order"),
        sa.ForeignKeyConstraint(["user_low_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_high_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_low_id", "user_high_id", name="uq_friendships_pair"),
    )
    op.create_index("idx_friendships_low", "friendships", ["user_low_id"])
    op.create_index("idx_friendships_high", "friendships", ["user_high_id"])

    op.add_column("rooms", sa.Column("title", sa.String(length=100), nullable=True))
    op.add_column("rooms", sa.Column("group_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_rooms_group_id_groups", "rooms", "groups", ["group_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("idx_rooms_group", "rooms", ["group_id", "created_at"])

    op.add_column("room_participants", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_room_participants_user_id_users",
        "room_participants",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_participants_room_user",
        "room_participants",
        ["room_id", "user_id"],
        unique=True,
    )

    op.add_column(
        "line_items",
        sa.Column(
            "allocation_mode",
            sa.String(length=20),
            server_default="individual",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_items_allocation_mode",
        "line_items",
        "allocation_mode IN ('individual','equal')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_items_allocation_mode", "line_items", type_="check")
    op.drop_column("line_items", "allocation_mode")
    op.drop_index("idx_participants_room_user", table_name="room_participants")
    op.drop_constraint(
        "fk_room_participants_user_id_users", "room_participants", type_="foreignkey"
    )
    op.drop_column("room_participants", "user_id")
    op.drop_index("idx_rooms_group", table_name="rooms")
    op.drop_constraint("fk_rooms_group_id_groups", "rooms", type_="foreignkey")
    op.drop_column("rooms", "group_id")
    op.drop_column("rooms", "title")
    op.drop_index("idx_friendships_high", table_name="friendships")
    op.drop_index("idx_friendships_low", table_name="friendships")
    op.drop_table("friendships")
    op.drop_index("idx_group_members_user", table_name="group_members")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "display_name")
    op.drop_column("users", "username")
