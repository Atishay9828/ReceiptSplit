"""
ReceiptSplit - Allocation Primitives

Two allocation strategies for distributing amounts across participants:

1. EqualAllocator:       floor(total / N), remainder round-robin by join order.
2. ProportionalAllocator: floor(total * share / sum_shares), remainder round-robin.

Both use integer arithmetic exclusively. No floats. No Decimal.
Both guarantee: sum(output.values()) == total_paise.

Design authority:
  - Phase 1 Implementation Design section 6.4
  - Amendment SE-1 (zero-denominator guard)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID


class EqualAllocator:
    """Distributes total_paise equally among participants.

    Remainder (total % N) is distributed 1 paise each to the first
    `remainder` participants in join order (round-robin).

    This is deterministic: same input always produces same output.

    Examples:
        301 / 3 participants => [101, 100, 100]
        100 / 3 participants => [34, 33, 33]
        1   / 3 participants => [1, 0, 0]
        0   / 3 participants => [0, 0, 0]
    """

    @staticmethod
    def allocate(
        total_paise: int,
        participants: list[UUID],
    ) -> dict[UUID, int]:
        """Distributes total_paise equally. Remainder round-robin.

        Args:
            total_paise:  Amount to distribute (>= 0).
            participants: List of participant IDs in join order.

        Returns:
            Dict mapping participant_id -> allocated paise.
            Guaranteed: sum(result.values()) == total_paise.
        """
        n = len(participants)
        if n == 0:
            return {}

        base = total_paise // n
        remainder = total_paise - (base * n)

        result: dict[UUID, int] = {}
        for i, pid in enumerate(participants):
            result[pid] = base + (1 if i < remainder else 0)

        return result


class ProportionalAllocator:
    """Distributes total_paise proportionally to per-participant shares.

    For each participant:
        portion = floor(total_paise * share[p] / sum(shares))
    Remainder is distributed round-robin by join order.

    Amendment SE-1: Zero-denominator guard.
    If sum(shares) == 0 (e.g., full discount scenario per PDD E6),
    falls back to EqualAllocator.

    This is deterministic: same input always produces same output.
    """

    @staticmethod
    def allocate(
        total_paise: int,
        shares: dict[UUID, int],
        round_robin_order: list[UUID],
    ) -> dict[UUID, int]:
        """Distributes total_paise proportionally to shares.

        Args:
            total_paise:       Amount to distribute (>= 0).
            shares:            participant_id -> their subtotal (basis for proportion).
            round_robin_order: Participant IDs in join order for remainder distribution.

        Returns:
            Dict mapping participant_id -> allocated paise.
            Guaranteed: sum(result.values()) == total_paise.
        """
        total_share = sum(shares.get(pid, 0) for pid in round_robin_order)

        # SE-1: Zero-denominator guard.
        # When all shares are zero (e.g., discount >= subtotal -> post-discount = 0),
        # proportional allocation is undefined. Fall back to equal split.
        # This is consistent with PDD §18.1 E6.
        if total_share == 0:
            return EqualAllocator.allocate(total_paise, round_robin_order)

        result: dict[UUID, int] = {}
        allocated = 0
        for pid in round_robin_order:
            share = shares.get(pid, 0)
            portion = (total_paise * share) // total_share
            result[pid] = portion
            allocated += portion

        remainder = total_paise - allocated
        # remainder is always >= 0 because we used floor division.
        # It is always < len(round_robin_order) because the max per-participant
        # truncation error is < 1.

        for i in range(remainder):
            pid = round_robin_order[i % len(round_robin_order)]
            result[pid] += 1

        return result
