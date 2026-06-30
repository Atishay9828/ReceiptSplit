"""
ReceiptSplit - Split Engine Exceptions

Split-specific exceptions raised during calculation.
These are distinct from validation errors (which are DomainErrors).
Split exceptions wrap SplitInvariantFailed for the API layer.
"""

from __future__ import annotations

from app.shared.errors import SplitInvariantFailed


class SumConservationViolation(SplitInvariantFailed):
    """sum(participant_totals) != grand_total_paise."""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(
            f"Sum conservation violated: expected={expected}, actual={actual}, "
            f"delta={actual - expected}"
        )


class NegativeTotalViolation(SplitInvariantFailed):
    """A participant's total_paise is negative."""

    def __init__(self, participant_id: str, total_paise: int) -> None:
        super().__init__(f"Negative total for participant {participant_id}: {total_paise} paise")


class NegativePayerTotalViolation(SplitInvariantFailed):
    """Payer's residual total is negative after rounding."""

    def __init__(
        self,
        payer_total: int,
        grand_total: int,
        others_sum: int,
    ) -> None:
        super().__init__(
            f"Payer total is negative: {payer_total} paise. "
            f"grand_total={grand_total}, others_sum={others_sum}"
        )


class AllocationConservationViolation(SplitInvariantFailed):
    """sum(allocated amounts) != total amount for an adjustment."""

    def __init__(self, adj_type: str, expected: int, actual: int) -> None:
        super().__init__(
            f"Allocation conservation violated for {adj_type}: "
            f"expected={expected}, actual={actual}"
        )
