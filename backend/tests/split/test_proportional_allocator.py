"""
Tests for ProportionalAllocator.

Covers:
  - Normal proportional distribution
  - Skewed shares (one participant has most)
  - Zero-denominator fallback (Amendment SE-1)
  - Remainder behavior
  - Single participant
  - All shares equal (should match EqualAllocator)
  - Large amounts
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.split.allocators import ProportionalAllocator


def _uuids(n: int) -> list:
    return [uuid4() for _ in range(n)]


@pytest.mark.unit
class TestProportionalAllocator:
    # ── Normal proportional ──────────────────────────────────────────────

    def test_simple_proportional(self):
        """60/40 split of 1000 paise => [600, 400]."""
        pids = _uuids(2)
        shares = {pids[0]: 60, pids[1]: 40}
        result = ProportionalAllocator.allocate(1000, shares, pids)
        assert result[pids[0]] == 600
        assert result[pids[1]] == 400
        assert sum(result.values()) == 1000

    def test_proportional_with_remainder(self):
        """1/3 each of 100 paise => [34, 33, 33]."""
        pids = _uuids(3)
        shares = {pids[0]: 100, pids[1]: 100, pids[2]: 100}
        result = ProportionalAllocator.allocate(100, shares, pids)
        assert sum(result.values()) == 100
        # 100 * 100 // 300 = 33 each, remainder = 1
        assert result[pids[0]] == 34  # first in round-robin gets extra
        assert result[pids[1]] == 33
        assert result[pids[2]] == 33

    def test_skewed_shares(self):
        """One person has 90% of the bill."""
        pids = _uuids(3)
        shares = {pids[0]: 9000, pids[1]: 500, pids[2]: 500}
        result = ProportionalAllocator.allocate(10000, shares, pids)
        assert sum(result.values()) == 10000
        assert result[pids[0]] == 9000
        assert result[pids[1]] == 500
        assert result[pids[2]] == 500

    def test_one_person_gets_everything(self):
        """One person has all shares."""
        pids = _uuids(3)
        shares = {pids[0]: 1000, pids[1]: 0, pids[2]: 0}
        result = ProportionalAllocator.allocate(500, shares, pids)
        assert result[pids[0]] == 500
        assert result[pids[1]] == 0
        assert result[pids[2]] == 0
        assert sum(result.values()) == 500

    # ── SE-1: Zero-denominator fallback ──────────────────────────────────

    def test_zero_denominator_falls_back_to_equal(self):
        """Amendment SE-1: all shares zero => equal allocation."""
        pids = _uuids(3)
        shares = {pids[0]: 0, pids[1]: 0, pids[2]: 0}
        result = ProportionalAllocator.allocate(300, shares, pids)
        assert sum(result.values()) == 300
        assert all(v == 100 for v in result.values())

    def test_zero_denominator_with_remainder(self):
        """SE-1: zero shares + remainder => equal with round-robin."""
        pids = _uuids(3)
        shares = {pids[0]: 0, pids[1]: 0, pids[2]: 0}
        result = ProportionalAllocator.allocate(301, shares, pids)
        assert sum(result.values()) == 301
        assert result[pids[0]] == 101  # first gets extra
        assert result[pids[1]] == 100
        assert result[pids[2]] == 100

    def test_zero_denominator_zero_total(self):
        """Zero shares and zero total => all zeros."""
        pids = _uuids(3)
        shares = {pids[0]: 0, pids[1]: 0, pids[2]: 0}
        result = ProportionalAllocator.allocate(0, shares, pids)
        assert all(v == 0 for v in result.values())

    # ── Remainder behavior ───────────────────────────────────────────────

    def test_remainder_goes_to_join_order(self):
        """Remainder distributed in join order, not by share size."""
        pids = _uuids(4)
        shares = {pids[0]: 1, pids[1]: 1, pids[2]: 1, pids[3]: 1}
        result = ProportionalAllocator.allocate(7, shares, pids)
        # 7 * 1 // 4 = 1 each, remainder = 3
        assert result[pids[0]] == 2  # first 3 get extra
        assert result[pids[1]] == 2
        assert result[pids[2]] == 2
        assert result[pids[3]] == 1
        assert sum(result.values()) == 7

    def test_missing_participant_in_shares(self):
        """Participant in round_robin but not in shares => treated as 0."""
        pids = _uuids(3)
        shares = {pids[0]: 500, pids[1]: 500}  # pids[2] missing
        result = ProportionalAllocator.allocate(1000, shares, pids)
        assert result[pids[2]] == 0
        assert sum(result.values()) == 1000

    # ── Single participant ───────────────────────────────────────────────

    def test_single_participant(self):
        pids = _uuids(1)
        shares = {pids[0]: 100}
        result = ProportionalAllocator.allocate(999, shares, pids)
        assert result[pids[0]] == 999

    # ── All shares equal ─────────────────────────────────────────────────

    def test_equal_shares_matches_equal_allocator(self):
        """When all shares are equal, proportional should give same result as equal."""
        pids = _uuids(5)
        shares = dict.fromkeys(pids, 100)
        result = ProportionalAllocator.allocate(1001, shares, pids)
        # 1001 / 5 = 200 each, remainder = 1
        assert result[pids[0]] == 201
        for pid in pids[1:]:
            assert result[pid] == 200
        assert sum(result.values()) == 1001

    # ── Large amounts ────────────────────────────────────────────────────

    def test_large_amounts(self):
        pids = _uuids(4)
        shares = {
            pids[0]: 50_000_000,
            pids[1]: 25_000_000,
            pids[2]: 15_000_000,
            pids[3]: 10_000_000,
        }
        result = ProportionalAllocator.allocate(100_000_000, shares, pids)
        assert sum(result.values()) == 100_000_000
        assert result[pids[0]] == 50_000_000
        assert result[pids[1]] == 25_000_000
        assert result[pids[2]] == 15_000_000
        assert result[pids[3]] == 10_000_000

    # ── Determinism ──────────────────────────────────────────────────────

    def test_deterministic(self):
        pids = _uuids(4)
        shares = {pids[0]: 337, pids[1]: 221, pids[2]: 442}
        result1 = ProportionalAllocator.allocate(5000, shares, pids)
        result2 = ProportionalAllocator.allocate(5000, shares, pids)
        assert result1 == result2

    # ── Sum conservation (parametrized) ──────────────────────────────────

    @pytest.mark.parametrize(
        ("total", "share_vals"),
        [
            (0, [100, 200, 300]),
            (1, [1, 1, 1]),
            (7, [3, 2, 2]),
            (100, [1, 0, 0]),
            (999, [333, 333, 333]),
            (100_000_000, [50_000_000, 30_000_000, 20_000_000]),
        ],
    )
    def test_sum_conservation(self, total: int, share_vals: list[int]):
        pids = _uuids(len(share_vals))
        shares = {pids[i]: share_vals[i] for i in range(len(share_vals))}
        result = ProportionalAllocator.allocate(total, shares, pids)
        assert sum(result.values()) == total

    # ── Non-negative values ──────────────────────────────────────────────

    @pytest.mark.parametrize("total", [0, 1, 50, 1000, 100_000])
    def test_all_values_non_negative(self, total: int):
        pids = _uuids(4)
        shares = {pids[0]: 100, pids[1]: 200, pids[2]: 50, pids[3]: 0}
        result = ProportionalAllocator.allocate(total, shares, pids)
        assert all(v >= 0 for v in result.values())
