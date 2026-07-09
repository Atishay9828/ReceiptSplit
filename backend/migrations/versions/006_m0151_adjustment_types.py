"""Expand adjustment type check constraint for M015.1.

Revision ID: 006_m0151_adjustment_types
Revises: 005_m013_security_hardening
Create Date: 2026-07-09
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "006_m0151_adjustment_types"
down_revision: str | None = "005_m013_security_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TYPES = (
    "'tax','service_charge','delivery_fee','packaging_fee','tip',"
    "'discount','coupon','offer','adjustment','rounding'"
)
OLD_TYPES = "'tax','service_charge','delivery_fee','discount','adjustment'"


def upgrade() -> None:
    op.drop_constraint("ck_adj_type", "split_adjustments", type_="check")
    op.create_check_constraint(
        "ck_adj_type",
        "split_adjustments",
        f"type IN ({NEW_TYPES})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_adj_type", "split_adjustments", type_="check")
    op.create_check_constraint(
        "ck_adj_type",
        "split_adjustments",
        f"type IN ({OLD_TYPES})",
    )

