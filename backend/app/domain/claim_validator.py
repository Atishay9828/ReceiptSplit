"""
ReceiptSplit — Claim Validator

Pure domain logic for validating claim/unclaim operations.
Isolates validation rules from the ItemService orchestration.

Design authority:
    - PDD §7 (Claiming)
    - Phase 1 Design Amendments
"""

from __future__ import annotations

from app.shared.errors import (
    InvalidClaimQuantity,
    InvalidStateTransition,
    WrongSplitMode,
)


class ClaimValidator:
    @staticmethod
    def validate_room_active(room_status: str) -> None:
        """A room must be active to allow claiming items."""
        if room_status != "active":
            raise InvalidStateTransition(
                from_state=room_status,
                to_state="claiming",
            )

    @staticmethod
    def validate_item_wise_mode(split_mode: str) -> None:
        """Claims are only valid in item-wise mode."""
        if split_mode != "item_wise":
            raise WrongSplitMode()

    @staticmethod
    def validate_quantity_available(
        claimed_qty: int, item_qty: int, already_claimed: int
    ) -> None:
        """
        Validates the requested claim quantity.
        Rules:
        - must be >= 1
        - cannot exceed (item_qty - already_claimed)
        """
        remaining = item_qty - already_claimed
        if claimed_qty < 1 or claimed_qty > remaining:
            raise InvalidClaimQuantity(max_qty=remaining)
