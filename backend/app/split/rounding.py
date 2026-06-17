"""
ReceiptSplit - Rounding Policy

Rounds non-payer totals down to the nearest rupee (100 paise).
The payer absorbs all rounding error as a residual.

Floor rounding (not round-half-up) is used to guarantee the payer's
residual is always non-negative. Round-half-up can push the sum of
non-payer totals above grand_total when multiple non-payers hit the
50-paise midpoint simultaneously.

Post-conditions (enforced — violation raises SplitInvariantFailed):
  1. sum(result.values()) == grand_total_paise
  2. result[payer_id] >= 0

Design authority:
  - Phase 1 Implementation Design section 6.5
  - Amendment SE-2 (payer non-negative assertion)
  - PDD section 5.4 (payer = residual)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.split.exceptions import (
    NegativePayerTotalViolation,
    SumConservationViolation,
)

if TYPE_CHECKING:
    from uuid import UUID


class RoundingPolicy:
    """Rounds split totals to the nearest rupee (floor).

    Algorithm:
      1. For each non-payer: floor raw total to nearest 100 paise (₹1).
      2. Payer total = grand_total - sum(all non-payer rounded totals).
      3. Assert sum == grand_total.
      4. Assert payer_total >= 0.

    Floor rounding formula (integer-only, no floats):
      rounded = (raw // 100) * 100

    Examples:
      - 150 paise -> 100 paise (floor)
      - 149 paise -> 100 paise (floor)
      - 50  paise -> 0   paise (floor)
      - 99  paise -> 0   paise (floor)
      - 100 paise -> 100 paise (exact)
      - 0   paise -> 0   paise (exact)

    Floor rounding guarantees: sum(rounded_non_payers) <= sum(raw_non_payers).
    Since raw totals are derived from the allocators which conserve sum,
    and payer = grand_total - sum(others), the payer total is always >= 0.
    """

    @staticmethod
    def apply(
        raw_totals: dict[UUID, int],
        grand_total_paise: int,
        payer_id: UUID,
    ) -> dict[UUID, int]:
        """Rounds totals and derives payer's share as residual.

        Args:
            raw_totals:       participant_id -> raw total in paise (pre-rounding).
            grand_total_paise: The exact grand total to conserve.
            payer_id:         UUID of the payer (creator).

        Returns:
            Dict mapping participant_id -> rounded total in paise.

        Raises:
            SumConservationViolation: if sum != grand_total_paise (bug).
            NegativePayerTotalViolation: if payer_total < 0 (bug).
        """
        rounded: dict[UUID, int] = {}
        others_sum = 0

        for pid, raw in raw_totals.items():
            if pid == payer_id:
                continue
            # Floor to nearest 100 paise (₹1). Always rounds down.
            # This guarantees others_sum <= grand_total.
            r = (raw // 100) * 100
            rounded[pid] = r
            others_sum += r

        # Payer total is the residual — never computed independently.
        # This guarantees sum conservation trivially.
        payer_total = grand_total_paise - others_sum
        rounded[payer_id] = payer_total

        # Invariant 1: Sum conservation.
        total = sum(rounded.values())
        if total != grand_total_paise:
            raise SumConservationViolation(
                expected=grand_total_paise, actual=total
            )

        # Invariant 2: Payer non-negative (Amendment SE-2).
        if payer_total < 0:
            raise NegativePayerTotalViolation(
                payer_total=payer_total,
                grand_total=grand_total_paise,
                others_sum=others_sum,
            )

        return rounded
