"""
ReceiptSplit - Split Invariant Checks

Dedicated invariant verification for the split engine output.
Called at the end of the calculation pipeline (step 13 of PDD §5.1).

All violations raise SplitInvariantFailed subclasses.
Never log-and-continue. Never auto-correct.

Design authority:
  - PDD section 5.0 (canonical invariant)
  - PDD section 5.1 step 13 (assert invariant)
  - Amendment SE-2 (payer non-negative)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.split.exceptions import (
    AllocationConservationViolation,
    NegativePayerTotalViolation,
    NegativeTotalViolation,
    SumConservationViolation,
)

if TYPE_CHECKING:
    from uuid import UUID

    from app.split.models import SplitResult

if True:
    pass



def check_sum_conservation(result: SplitResult) -> None:
    """Verify: sum(participant_totals) == grand_total_paise.

    PDD §5.0: "At every step, and in the final output:
    sum(all participant totals) == grand_total_paise.
    If this assertion fails, it is a bug."

    Raises:
        SumConservationViolation: if the sum does not match.
    """
    actual = sum(t.total_paise for t in result.participant_totals)
    if actual != result.grand_total_paise:
        raise SumConservationViolation(
            expected=result.grand_total_paise, actual=actual
        )


def check_non_negative_totals(result: SplitResult) -> None:
    """Verify: all(total_paise >= 0) for every participant.

    Raises:
        NegativeTotalViolation: if any participant has a negative total.
    """
    for t in result.participant_totals:
        if t.total_paise < 0:
            raise NegativeTotalViolation(
                participant_id=str(t.participant_id),
                total_paise=t.total_paise,
            )


def check_payer_non_negative(result: SplitResult) -> None:
    """Verify: payer's total_paise >= 0.

    Amendment SE-2: The payer's total is grand_total - sum(others).
    A negative payer total means the rounding or allocation is defective.

    Raises:
        NegativePayerTotalViolation: if the payer's total is negative.
    """
    for t in result.participant_totals:
        if t.is_payer and t.total_paise < 0:
            others_sum = sum(
                o.total_paise
                for o in result.participant_totals
                if not o.is_payer
            )
            raise NegativePayerTotalViolation(
                payer_total=t.total_paise,
                grand_total=result.grand_total_paise,
                others_sum=others_sum,
            )


def check_allocation_conservation(
    allocated: dict[UUID, int],
    expected_total: int,
    adj_type: str,
) -> None:
    """Verify: sum(allocated amounts) == total amount for an adjustment.

    Called after each allocator run to verify correctness.

    Raises:
        AllocationConservationViolation: if the sum does not match.
    """
    actual = sum(allocated.values())
    if actual != expected_total:
        raise AllocationConservationViolation(
            adj_type=adj_type, expected=expected_total, actual=actual
        )


def check_all_invariants(result: SplitResult) -> None:
    """Run all invariant checks on a SplitResult.

    This is the final step of the split calculation pipeline (PDD §5.1 step 13).
    If any check fails, the entire split is rejected with SPLIT_INVARIANT_FAILED.
    """
    check_sum_conservation(result)
    check_non_negative_totals(result)
    check_payer_non_negative(result)
