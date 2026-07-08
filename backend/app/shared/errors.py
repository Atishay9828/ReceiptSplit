"""
ReceiptSplit — Domain Error Hierarchy

All application errors are subclasses of `DomainError`.
Each error carries a machine-readable `code` (used in the API error response)
and a human-readable `message`.

HTTP status codes are assigned at the API layer (routers), not here.
The domain layer only raises `DomainError` subclasses.

Error code catalog matches PDD §16.2 exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Base ──────────────────────────────────────────────────────────────────────


@dataclass
class DomainError(Exception):
    """
    Base class for all ReceiptSplit domain errors.

    Attributes:
        code:    Machine-readable error code string (e.g. 'ITEM_ALREADY_CLAIMED').
        message: Human-readable description (shown to users).
        details: Optional dict of extra context (item IDs, names, etc.).
    """

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Serialises to the API error response shape (PDD §16.1)."""
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


# ── 400 Validation Errors ─────────────────────────────────────────────────────


class InvalidVPAFormat(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_VPA_FORMAT",
            message="Enter a valid UPI ID (e.g., name@upi).",
        )


class InvalidClaimQuantity(DomainError):
    def __init__(self, max_qty: int) -> None:
        super().__init__(
            code="INVALID_CLAIM_QUANTITY",
            message=f"You can claim 1 to {max_qty} of this item.",
            details={"max_qty": max_qty},
        )


class InvalidItemName(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_ITEM_NAME",
            message="Item name must be 1-200 characters.",
        )


class InvalidNickname(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_NICKNAME",
            message="Nickname must be 1-30 characters.",
        )


class InvalidColor(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_COLOR",
            message="Participant color must be one of the allowed palette colors.",
        )


class AmountTooLarge(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="AMOUNT_TOO_LARGE",
            message="Amount exceeds the maximum allowed.",
        )


class MaxItemsExceeded(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="MAX_ITEMS_EXCEEDED",
            message="Maximum 100 items per receipt.",
        )


class MaxAdjustmentsExceeded(DomainError):
    def __init__(self, adj_type: str) -> None:
        super().__init__(
            code="MAX_ADJUSTMENTS_EXCEEDED",
            message=f"Maximum 10 lines per adjustment category ({adj_type}).",
            details={"type": adj_type},
        )


class ItemQuantityZero(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ITEM_QUANTITY_ZERO",
            message="Quantity must be at least 1.",
        )


class QuantityBelowClaimed(DomainError):
    def __init__(self, claimed_qty: int) -> None:
        super().__init__(
            code="QUANTITY_BELOW_CLAIMED",
            message=f"{claimed_qty} unit(s) are already claimed. Release some claims first.",
            details={"claimed_qty": claimed_qty},
        )


class NoItems(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="NO_ITEMS",
            message="Add at least one item before opening for claiming.",
        )


class InvalidAdjustmentAmount(DomainError):
    def __init__(self, adj_type: str) -> None:
        super().__init__(
            code="INVALID_ADJUSTMENT_AMOUNT",
            message=f"Amount must be >= 0 for adjustment type '{adj_type}'.",
            details={"type": adj_type},
        )


class PercentagesNotOneHundred(DomainError):
    """Post-MVP: percentage split validation."""

    def __init__(self) -> None:
        super().__init__(
            code="PERCENTAGES_NOT_100",
            message="Percentages must total 100%.",
        )


# ── 403 Authorization Errors ──────────────────────────────────────────────────


class RoomFull(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ROOM_FULL",
            message="This bill has reached the max of 20 people.",
        )


class RoomExpired(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ROOM_EXPIRED",
            message="This bill has expired.",
        )


class RoomClosed(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ROOM_CLOSED",
            message="This bill is no longer accepting participants.",
        )


class NotAuthorized(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="NOT_AUTHORIZED",
            message="You don't have permission to do this.",
        )


class InvalidToken(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_TOKEN",
            message="This link is invalid or has expired.",
        )


class RateLimitExceeded(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="RATE_LIMITED",
            message="Too many attempts. Please try again later.",
        )


# ── 404 Not Found ─────────────────────────────────────────────────────────────


class RoomNotFound(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ROOM_NOT_FOUND",
            message="Bill not found.",
        )


class ItemNotFound(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ITEM_NOT_FOUND",
            message="Item not found.",
        )


# ── 409 Conflict ──────────────────────────────────────────────────────────────


class ItemAlreadyClaimed(DomainError):
    def __init__(self, item_name: str, claimed_by: str, remaining_qty: int) -> None:
        super().__init__(
            code="ITEM_ALREADY_CLAIMED",
            message=f"{item_name} was just claimed by {claimed_by}.",
            details={
                "claimed_by": claimed_by,
                "remaining_qty": remaining_qty,
            },
        )


class VersionConflict(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VERSION_CONFLICT",
            message="Someone just made a change. Refreshing…",
        )


class InvalidStateTransition(DomainError):
    def __init__(self, from_state: str, to_state: str) -> None:
        super().__init__(
            code="INVALID_STATE_TRANSITION",
            message="This action isn't available right now.",
            details={"from": from_state, "to": to_state},
        )


class ItemHasClaims(DomainError):
    def __init__(self, claimed_by: list[str]) -> None:
        super().__init__(
            code="ITEM_HAS_CLAIMS",
            message="This item is claimed. Confirm to release all claims and delete.",
            details={"claimed_by": claimed_by},
        )


class WrongSplitMode(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="WRONG_SPLIT_MODE",
            message="Claiming is only available in item-wise mode.",
        )


# ── 422 Semantic Errors ───────────────────────────────────────────────────────


class UnclaimedItemsExist(DomainError):
    def __init__(self, item_names: list[str]) -> None:
        super().__init__(
            code="UNCLAIMED_ITEMS_EXIST",
            message=f"{len(item_names)} item(s) are unclaimed.",
            details={"unclaimed_items": item_names},
        )


class VPANotSet(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VPA_NOT_SET",
            message="Set your UPI ID before settling.",
        )


class InsufficientParticipants(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="INSUFFICIENT_PARTICIPANTS",
            message="At least one other person must join before locking.",
        )


# ── 423 Locked ────────────────────────────────────────────────────────────────


class RoomLocked(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ROOM_LOCKED",
            message="Bill is locked. Ask the creator to unlock.",
        )


class RoomAlreadyLocked(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ROOM_ALREADY_LOCKED",
            message="This bill is already locked.",
        )


class ReceiptLocked(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="RECEIPT_LOCKED",
            message="Receipt can't be replaced while items are claimed.",
        )


# ── 500 Internal Errors ───────────────────────────────────────────────────────


class SplitInvariantFailed(DomainError):
    """
    Raised when the split engine's invariant assertion fails.
    This is always a bug — engineering must be alerted.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(
            code="SPLIT_INVARIANT_FAILED",
            message="Calculation error. Please try again.",
            details={"internal_detail": detail},
        )


class InternalError(DomainError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(
            code="INTERNAL_ERROR",
            message="Something went wrong.",
            details={"detail": detail} if detail else {},
        )
