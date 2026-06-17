"""
Tests for RoundingPolicy.

Covers:
  - Already-round amounts (no-op)
  - Normal rounding (up and down)
  - ₹0.50 rounding (midpoint rounds up)
  - Payer absorbs rounding loss
  - Payer absorbs rounding gain
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

    # ── Normal rounding ──────────────────────────────────────────────────

    def test_round_down(self):
        """149 paise rounds down to 100."""
        payer, others = _payer_and_others(1)
        raw = {payer: 851, others[0]: 149}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 100
        assert result[payer] == 900  # absorbs 51 paise gain
        assert sum(result.values()) == 1000

    def test_round_up(self):
        """151 paise rounds up to 200."""
        payer, others = _payer_and_others(1)
        raw = {payer: 849, others[0]: 151}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 200
        assert result[payer] == 800  # absorbs 49 paise loss
        assert sum(result.values()) == 1000

    # ── Midpoint rounding ────────────────────────────────────────────────

    def test_midpoint_rounds_up(self):
        """50 paise (midpoint) rounds up to 100 via integer formula."""
        payer, others = _payer_and_others(1)
        raw = {payer: 950, others[0]: 50}
        result = RoundingPolicy.apply(raw, 1000, payer)
        # ((50 + 50) // 100) * 100 = 100
        assert result[others[0]] == 100
        assert result[payer] == 900
        assert sum(result.values()) == 1000

    def test_250_rounds_to_300(self):
        """250 paise: ((250 + 50) // 100) * 100 = 300."""
        payer, others = _payer_and_others(1)
        raw = {payer: 750, others[0]: 250}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 300
        assert result[payer] == 700
        assert sum(result.values()) == 1000

    # ── Payer absorbs rounding error ─────────────────────────────────────

    def test_payer_absorbs_loss(self):
        """Non-payers round up => payer's share decreases."""
        payer, others = _payer_and_others(3)
        # Each non-payer has 333 paise => rounds to 300.
        # But let's test rounding up: 351 -> 400
        raw = {payer: 697, others[0]: 101, others[1]: 101, others[2]: 101}
        result = RoundingPolicy.apply(raw, 1000, payer)
        # 101 -> ((101+50)//100)*100 = 100
        assert all(result[o] == 100 for o in others)
        assert result[payer] == 700
        assert sum(result.values()) == 1000

    def test_payer_absorbs_gain(self):
        """Non-payers round down => payer's share increases."""
        payer, others = _payer_and_others(3)
        raw = {payer: 703, others[0]: 99, others[1]: 99, others[2]: 99}
        result = RoundingPolicy.apply(raw, 1000, payer)
        # 99 -> ((99+50)//100)*100 = 100
        assert all(result[o] == 100 for o in others)
        assert result[payer] == 700
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
        """Only one non-payer."""
        payer, others = _payer_and_others(1)
        raw = {payer: 7533, others[0]: 2467}
        result = RoundingPolicy.apply(raw, 10000, payer)
        assert result[others[0]] == 2500  # 2467 -> 2500
        assert result[payer] == 7500
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
        """1 paise for non-payer rounds to 0 via ((1+50)//100)*100 = 0."""
        payer, others = _payer_and_others(1)
        raw = {payer: 99, others[0]: 1}
        result = RoundingPolicy.apply(raw, 100, payer)
        # ((1+50)//100)*100 = (51//100)*100 = 0*100 = 0
        assert result[others[0]] == 0
        assert result[payer] == 100
        assert sum(result.values()) == 100

    def test_49_paise_rounds_to_0(self):
        """49 paise: ((49+50)//100)*100 = 0."""
        payer, others = _payer_and_others(1)
        raw = {payer: 951, others[0]: 49}
        result = RoundingPolicy.apply(raw, 1000, payer)
        # ((49+50)//100)*100 = (99//100)*100 = 0
        assert result[others[0]] == 0
        assert result[payer] == 1000
        assert sum(result.values()) == 1000

    def test_payer_total_zero_is_valid(self):
        """Payer can have exactly 0."""
        payer, others = _payer_and_others(1)
        raw = {payer: 0, others[0]: 1000}
        result = RoundingPolicy.apply(raw, 1000, payer)
        assert result[others[0]] == 1000
        assert result[payer] == 0
        assert sum(result.values()) == 1000

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
        """If non-payer rounding pushes total above grand, payer goes negative."""
        payer, others = _payer_and_others(2)
        # Construct a scenario where sum of rounded non-payer totals > grand.
        # others each get 550 paise, rounds to 600 each. Grand total = 1000.
        # Sum of rounded = 1200 > 1000 => payer = -200.
        raw = {payer: -100, others[0]: 550, others[1]: 550}
        with pytest.raises(NegativePayerTotalViolation):
            RoundingPolicy.apply(raw, 1000, payer)
