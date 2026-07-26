"""Track partial settlement claims and confirmed amounts.

Revision ID: 008_partial_settlements
Revises: 007_persistent_rooms
Create Date: 2026-07-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "008_partial_settlements"
down_revision: str | None = "007_persistent_rooms"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "settlement_requests",
        sa.Column(
            "confirmed_amount_paise",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "settlement_requests",
        sa.Column("pending_claim_amount_paise", sa.BigInteger(), nullable=True),
    )
    op.execute(
        """
        UPDATE settlement_requests
        SET confirmed_amount_paise = amount_paise
        WHERE status = 'payer_confirmed'
        """
    )
    op.execute(
        """
        UPDATE settlement_requests
        SET pending_claim_amount_paise = amount_paise
        WHERE status = 'claimed_paid'
        """
    )
    op.create_check_constraint(
        "ck_settlement_requests_confirmed_amount",
        "settlement_requests",
        "confirmed_amount_paise >= 0 AND confirmed_amount_paise <= amount_paise",
    )
    op.create_check_constraint(
        "ck_settlement_requests_pending_claim_amount",
        "settlement_requests",
        "pending_claim_amount_paise IS NULL OR "
        "(pending_claim_amount_paise > 0 AND "
        "pending_claim_amount_paise <= amount_paise - confirmed_amount_paise)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_settlement_requests_pending_claim_amount",
        "settlement_requests",
        type_="check",
    )
    op.drop_constraint(
        "ck_settlement_requests_confirmed_amount",
        "settlement_requests",
        type_="check",
    )
    op.drop_column("settlement_requests", "pending_claim_amount_paise")
    op.drop_column("settlement_requests", "confirmed_amount_paise")
