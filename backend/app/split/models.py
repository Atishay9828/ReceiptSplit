"""
ReceiptSplit - Split Engine Domain Models

Frozen dataclasses used as the input/output contract for the split engine.
These are pure data carriers with no business logic.

All money fields are integer paise. No floats. No Decimal in the split path.

Design authority: Phase 1 Implementation Design section 6.2
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

if True:
    pass


# ── Input Models ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SplitItem:
    """A single line item on the receipt.

    Attributes:
        id:          Unique item identifier.
        quantity:    Number of units (>= 1, <= 999).
        total_paise: Total price for all units of this item (>= 0).
    """

    id: UUID
    quantity: int
    total_paise: int


@dataclass(frozen=True, slots=True)
class SplitAssignment:
    """A participant's claim on a specific item.

    Used only in item_wise mode. Empty list for equal mode.

    Attributes:
        item_id:        Which item is claimed.
        participant_id: Who claimed it.
        claimed_qty:    How many units they claimed (>= 1).
        created_at:     Claim timestamp, used to determine "last claimer"
                        for per-item remainder distribution.
    """

    item_id: UUID
    participant_id: UUID
    claimed_qty: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SplitAdjustment:
    """A tax, fee, discount, or adjustment line.

    Attributes:
        type:       One of: tax, service_charge, delivery_fee, discount, adjustment
        amount_paise: The adjustment amount. Non-negative for all types except
                      'adjustment' which may be negative (OCR reconciliation).
        allocation: How to distribute: 'proportional' or 'equal'.
    """

    type: str
    amount_paise: int
    allocation: str


@dataclass(frozen=True, slots=True)
class SplitParticipant:
    """A participant in the split.

    Attributes:
        id:         Participant UUID.
        is_payer:   True if this is the payer (creator). Exactly one per split.
        join_order: 0 = payer (earliest). Determines round-robin order.
    """

    id: UUID
    is_payer: bool
    join_order: int


@dataclass(frozen=True, slots=True)
class SplitInput:
    """Complete input to the split calculation engine.

    Invariants:
        - len(participants) >= 2
        - Exactly one participant has is_payer=True
        - participants sorted by join_order ascending
        - mode is 'equal' or 'item_wise'
        - In item_wise mode: every item must be fully assigned
        - All item total_paise >= 0
        - All item quantities >= 1
    """

    mode: str
    items: list[SplitItem]
    assignments: list[SplitAssignment]
    adjustments: list[SplitAdjustment]
    participants: list[SplitParticipant]


# ── Output Models ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ParticipantBreakdown:
    """Per-participant detailed breakdown of the split.

    All fields are integer paise. total_paise is the final amount.
    For the payer, total_paise is the residual (grand_total - sum(others)).
    """

    participant_id: UUID
    items_paise: int
    discount_paise: int
    tax_paise: int
    service_charge_paise: int
    delivery_fee_paise: int
    adjustment_paise: int
    total_paise: int
    is_payer: bool


@dataclass(frozen=True, slots=True)
class SplitResult:
    """Output of the split calculation engine.

    Invariants (enforced — violation is a bug):
        - sum(t.total_paise for t in participant_totals) == grand_total_paise
        - all(t.total_paise >= 0 for t in participant_totals)
        - invariant_holds is True
    """

    grand_total_paise: int
    participant_totals: list[ParticipantBreakdown]
    invariant_holds: bool
