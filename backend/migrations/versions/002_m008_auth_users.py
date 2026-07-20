"""Add authenticated users and room ownership.

Revision ID: 002_m008_auth_users
Revises: 001
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "002_m008_auth_users"
down_revision: str | None = "001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "subject", name="uq_users_provider_subject"),
    )
    op.add_column("rooms", sa.Column("creator_user_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_rooms_creator_user_id_users",
        "rooms",
        "users",
        ["creator_user_id"],
        ["id"],
    )
    op.create_index("idx_rooms_creator_user", "rooms", ["creator_user_id"])


def downgrade() -> None:
    op.drop_index("idx_rooms_creator_user", table_name="rooms")
    op.drop_constraint("fk_rooms_creator_user_id_users", "rooms", type_="foreignkey")
    op.drop_column("rooms", "creator_user_id")
    op.drop_table("users")
