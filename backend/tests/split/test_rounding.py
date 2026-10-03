"""
Tests for RoundingPolicy.

Covers:
  - Already-round amounts (no-op)
  - Exact paise preservation
  - Payer absorbs only the allocated remainder
  - All-zero totals
  - Single non-payer
  - Many non-payers (19)
  - Sum conservation
  - Payer non-negative
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.split.exceptions import NegativePayerTotalViolation
from app.split.rounding import RoundingPolicy


def _payer_and_others(n_others: int):
    payer = uuid4()
    others = [uuid4() for _ in range(n_others)]
    return payer, others


@pytest.mark.unit
class TestRoundingPolicy:
    # ── Already-round amounts ────────────────────────────────────────────

    def test_already_round_no_change(self):
        """Amounts already multiples of 100 => no rounding needed."""
        payer, others = _payer_and_others(2)
        raw = {payer: 5000, others[0]: 3000, others[1]: 2000}
        result = RoundingPolicy.apply(raw, 10000, payer)
        assert result == {payer: 5000, others[0]: 3000, others[1]: 2000}
        assert sum(result.values()) == 10000

    # ── Exact paise preservation ────────────────────────────────────────

    def test_149_paise_is_preserved(self):
        payer, others = _payer_and_others(1)
        raw = {payer: 851, others[0]: 149}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 149
        assert result[payer] == 851
        assert sum(result.values()) == 1000

    def test_151_paise_is_preserved(self):
        payer, others = _payer_and_others(1)
        raw = {payer: 849, others[0]: 151}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 151
        assert result[payer] == 849
        assert sum(result.values()) == 1000

    def test_midpoint_paise_is_preserved(self):
        payer, others = _payer_and_others(1)
        raw = {payer: 950, others[0]: 50}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 50
        assert result[payer] == 950
        assert sum(result.values()) == 1000

    def test_250_paise_is_preserved(self):
        payer, others = _payer_and_others(1)
        raw = {payer: 750, others[0]: 250}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 250
        assert result[payer] == 750
        assert sum(result.values()) == 1000

    def test_99_paise_is_preserved(self):
        payer, others = _payer_and_others(1)
        raw = {payer: 901, others[0]: 99}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 99
        assert result[payer] == 901
        assert sum(result.values()) == 1000

    # ── Payer absorbs rounding remainder ─────────────────────────────────

    def test_payer_absorbs_only_allocator_remainder(self):
        payer, others = _payer_and_others(3)
        raw = {payer: 697, others[0]: 101, others[1]: 101, others[2]: 101}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert all(result[o] == 101 for o in others)
        assert result[payer] == 697
        assert sum(result.values()) == 1000

    def test_payer_preserves_sub_rupee_non_payer_totals(self):
        payer, others = _payer_and_others(3)
        raw = {payer: 703, others[0]: 99, others[1]: 99, others[2]: 99}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert all(result[o] == 99 for o in others)
        assert result[payer] == 703
        assert sum(result.values()) == 1000

    # ── Edge cases ───────────────────────────────────────────────────────

    def test_all_zero_totals(self):
        """Grand total is 0 => all rounded to 0."""
        payer, others = _payer_and_others(2)
        raw = {payer: 0, others[0]: 0, others[1]: 0}
        result = RoundingPolicy.apply(raw, 0, payer)
        assert all(v == 0 for v in result.values())
        assert sum(result.values()) == 0

    def test_single_non_payer(self):
        """Only one non-payer; all allocated paise are preserved."""
        payer, others = _payer_and_others(1)
        raw = {payer: 7533, others[0]: 2467}
        result = RoundingPolicy.apply(raw, 10000, payer)
        assert result[others[0]] == 2467
        assert result[payer] == 7533
        assert sum(result.values()) == 10000

    def test_19_non_payers(self):
        """Maximum non-payers (19 + 1 payer = 20 room max)."""
        payer, others = _payer_and_others(19)
        raw = dict.fromkeys(others, 500)
        raw[payer] = 500
        grand = sum(raw.values())
        result = RoundingPolicy.apply(raw, grand, payer)
        assert sum(result.values()) == grand
        # 500 is already round
        assert all(result[o] == 500 for o in others)

    def test_very_small_amounts(self):
        """1 paise for non-payer remains 1 paise."""
        payer, others = _payer_and_others(1)
        raw = {payer: 99, others[0]: 1}
        result = RoundingPolicy.apply(raw, 100, payer)
        assert result[others[0]] == 1
        assert result[payer] == 99
        assert sum(result.values()) == 100

    def test_payer_total_zero_is_valid(self):
        """Payer can have exactly 0."""
        payer, others = _payer_and_others(1)
        raw = {payer: 0, others[0]: 1000}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 1000
        assert result[payer] == 0
        assert sum(result.values()) == 1000

    def test_150_paise_3_people(self):
        """The falsifying example: 150 paise / 3 people.
        Each gets 50 paise, with no rounding loss."""
        payer, others = _payer_and_others(2)
        raw = {payer: 50, others[0]: 50, others[1]: 50}
        result = RoundingPolicy.apply(raw, 150, payer)
        assert result[others[0]] == 50
        assert result[others[1]] == 50
        assert result[payer] == 50
        assert sum(result.values()) == 150

    # ── Sum conservation (parametrized) ──────────────────────────────────

    @pytest.mark.parametrize(
        ("payer_raw", "other_raws", "grand"),
        [
            (500, [500], 1000),
            (333, [333, 334], 1000),
            (0, [500, 500], 1000),
            (1, [1, 1, 1], 4),
            (50000, [25000, 15000, 10000], 100000),
        ],
    )
    def test_sum_conservation(self, payer_raw: int, other_raws: list[int], grand: int):
        payer, others = _payer_and_others(len(other_raws))
        raw = {payer: payer_raw}
        for i, o in enumerate(others):
            raw[o] = other_raws[i]
        result = RoundingPolicy.apply(raw, grand, payer)
        assert sum(result.values()) == grand

    # ── Invariant assertions ─────────────────────────────────────────────

    def test_negative_payer_total_raises(self):
        """Reject inputs whose non-payer allocations exceed the grand total."""
        payer, others = _payer_and_others(1)
        # Non-payer has 1100 raw. Grand = 1000.
        # Payer = 1000 - 1100 = -100.
        raw = {payer: -100, others[0]: 1100}
        with pytest.raises(NegativePayerTotalViolation):
            RoundingPolicy.apply(raw, 1000, payer)
