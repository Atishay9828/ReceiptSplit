"""
Tests for EqualAllocator.

Covers:
  - Exact division (no remainder)
  - Remainder distribution
  - 1 participant
  - 20 participants (max room size)
  - Zero total
  - 1 paise among many
  - Large amounts
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.split.allocators import EqualAllocator


def _uuids(n: int) -> list:
    return [uuid4() for _ in range(n)]


@pytest.mark.unit
class TestEqualAllocator:
    # ── Exact division ───────────────────────────────────────────────────

    def test_exact_division_2(self):
        pids = _uuids(2)
        result = EqualAllocator.allocate(200, pids)
        assert result == {pids[0]: 100, pids[1]: 100}
        assert sum(result.values()) == 200

    def test_exact_division_4(self):
        pids = _uuids(4)
        result = EqualAllocator.allocate(400, pids)
        assert all(v == 100 for v in result.values())
        assert sum(result.values()) == 400

    # ── Remainder distribution ───────────────────────────────────────────

    def test_remainder_1_paise(self):
        """301 / 3 => [101, 100, 100]."""
        pids = _uuids(3)
        result = EqualAllocator.allocate(301, pids)
        assert result[pids[0]] == 101  # first in join order gets extra
        assert result[pids[1]] == 100
        assert result[pids[2]] == 100
        assert sum(result.values()) == 301

    def test_remainder_2_paise(self):
        """302 / 3 => [101, 101, 100]."""
        pids = _uuids(3)
        result = EqualAllocator.allocate(302, pids)
        assert result[pids[0]] == 101
        assert result[pids[1]] == 101
        assert result[pids[2]] == 100
        assert sum(result.values()) == 302

    def test_remainder_equals_n_minus_1(self):
        """4 / 5 => [1, 1, 1, 1, 0]."""
        pids = _uuids(5)
        result = EqualAllocator.allocate(4, pids)
        values = [result[pid] for pid in pids]
        assert values == [1, 1, 1, 1, 0]
        assert sum(result.values()) == 4

    # ── Edge cases ───────────────────────────────────────────────────────

    def test_1_participant(self):
        pids = _uuids(1)
        result = EqualAllocator.allocate(999, pids)
        assert result[pids[0]] == 999
        assert sum(result.values()) == 999

    def test_20_participants(self):
        pids = _uuids(20)
        result = EqualAllocator.allocate(10000, pids)
        assert all(v == 500 for v in result.values())
        assert sum(result.values()) == 10000

    def test_20_participants_with_remainder(self):
        pids = _uuids(20)
        result = EqualAllocator.allocate(10013, pids)
        values = sorted(result.values(), reverse=True)
        assert values[:13] == [501] * 13
        assert values[13:] == [500] * 7
        assert sum(result.values()) == 10013

    def test_zero_total(self):
        pids = _uuids(3)
        result = EqualAllocator.allocate(0, pids)
        assert all(v == 0 for v in result.values())
        assert sum(result.values()) == 0

    def test_1_paise_3_participants(self):
        """PDD E9: 1 paise split among 3 => [1, 0, 0]."""
        pids = _uuids(3)
        result = EqualAllocator.allocate(1, pids)
        assert result[pids[0]] == 1
        assert result[pids[1]] == 0
        assert result[pids[2]] == 0
        assert sum(result.values()) == 1

    def test_empty_participants(self):
        result = EqualAllocator.allocate(100, [])
        assert result == {}

    def test_large_amount(self):
        pids = _uuids(3)
        result = EqualAllocator.allocate(100_000_000, pids)
        assert sum(result.values()) == 100_000_000
        # 100M / 3 = 33333333 * 3 = 99999999, remainder = 1
        assert result[pids[0]] == 33_333_334
        assert result[pids[1]] == 33_333_333
        assert result[pids[2]] == 33_333_333

    # ── Determinism ──────────────────────────────────────────────────────

    def test_deterministic(self):
        """Same input produces same output."""
        pids = _uuids(5)
        result1 = EqualAllocator.allocate(1001, pids)
        result2 = EqualAllocator.allocate(1001, pids)
        assert result1 == result2

    # ── Sum conservation (parametrized) ──────────────────────────────────

    @pytest.mark.parametrize(
        ("total", "n"),
        [
            (0, 1),
            (1, 1),
            (1, 20),
            (7, 3),
            (100, 7),
            (999, 13),
            (10001, 20),
            (100_000_000, 19),
        ],
    )
    def test_sum_conservation(self, total: int, n: int):
        pids = _uuids(n)
        result = EqualAllocator.allocate(total, pids)
        assert sum(result.values()) == total

    # ── Non-negative values ──────────────────────────────────────────────

    @pytest.mark.parametrize("total", [0, 1, 7, 100, 10000])
    def test_all_values_non_negative(self, total: int):
        pids = _uuids(5)
        result = EqualAllocator.allocate(total, pids)
        assert all(v >= 0 for v in result.values())
