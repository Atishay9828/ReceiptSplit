"""
Property-based tests for the split engine using Hypothesis.

Required properties (per user specification):
  1. Sum conservation: sum(result.totals) == grand_total
  2. No negative totals: all(total >= 0)
  3. Payer non-negative: payer_total >= 0
  4. Determinism: calculate(input) == calculate(input)

These tests run with max_examples=10000 for invariant tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.split.allocators import EqualAllocator, ProportionalAllocator
from app.split.calculator import SplitCalculator
from app.split.models import (
    SplitAdjustment,
    SplitAssignment,
    SplitInput,
    SplitItem,
    SplitParticipant,
)
from app.split.rounding import RoundingPolicy

# ── Custom strategies ────────────────────────────────────────────────────────

def _paise_amount():
    """Non-negative paise amount up to ₹1,00,000 (10,000,000 paise)."""
    return st.integers(min_value=0, max_value=10_000_000)


def _participant_count():
    """2 to 20 participants per room."""
    return st.integers(min_value=2, max_value=20)


# ── EqualAllocator properties ────────────────────────────────────────────────

@pytest.mark.unit
class TestEqualAllocatorProperties:
    @given(
        total=st.integers(min_value=0, max_value=100_000_000),
        n=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=10_000, suppress_health_check=[HealthCheck.too_slow])
    def test_sum_conservation(self, total: int, n: int):
        pids = [uuid4() for _ in range(n)]
        result = EqualAllocator.allocate(total, pids)
        assert sum(result.values()) == total

    @given(
        total=st.integers(min_value=0, max_value=100_000_000),
        n=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=10_000, suppress_health_check=[HealthCheck.too_slow])
    def test_non_negative(self, total: int, n: int):
        pids = [uuid4() for _ in range(n)]
        result = EqualAllocator.allocate(total, pids)
        assert all(v >= 0 for v in result.values())

    @given(
        total=st.integers(min_value=0, max_value=100_000_000),
        n=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=1_000, suppress_health_check=[HealthCheck.too_slow])
    def test_determinism(self, total: int, n: int):
        pids = [uuid4() for _ in range(n)]
        r1 = EqualAllocator.allocate(total, pids)
        r2 = EqualAllocator.allocate(total, pids)
        assert r1 == r2


# ── ProportionalAllocator properties ─────────────────────────────────────────

@pytest.mark.unit
class TestProportionalAllocatorProperties:
    @given(
        total=st.integers(min_value=0, max_value=100_000_000),
        share_list=st.lists(
            st.integers(min_value=0, max_value=10_000_000),
            min_size=1, max_size=20,
        ),
    )
    @settings(max_examples=10_000, suppress_health_check=[HealthCheck.too_slow])
    def test_sum_conservation(self, total: int, share_list: list[int]):
        pids = [uuid4() for _ in range(len(share_list))]
        shares = dict(zip(pids, share_list, strict=False))
        result = ProportionalAllocator.allocate(total, shares, pids)
        assert sum(result.values()) == total

    @given(
        total=st.integers(min_value=0, max_value=100_000_000),
        share_list=st.lists(
            st.integers(min_value=0, max_value=10_000_000),
            min_size=1, max_size=20,
        ),
    )
    @settings(max_examples=10_000, suppress_health_check=[HealthCheck.too_slow])
    def test_non_negative(self, total: int, share_list: list[int]):
        pids = [uuid4() for _ in range(len(share_list))]
        shares = dict(zip(pids, share_list, strict=False))
        result = ProportionalAllocator.allocate(total, shares, pids)
        assert all(v >= 0 for v in result.values())


# ── RoundingPolicy properties ────────────────────────────────────────────────

@pytest.mark.unit
class TestRoundingPolicyProperties:
    @given(
        grand_total=st.integers(min_value=0, max_value=100_000_000),
        n_non_payers=st.integers(min_value=1, max_value=19),
    )
    @settings(max_examples=10_000, suppress_health_check=[HealthCheck.too_slow])
    def test_sum_conservation(self, grand_total: int, n_non_payers: int):
        """Sum of rounded totals always equals grand_total."""
        payer_id = uuid4()
        non_payer_ids = [uuid4() for _ in range(n_non_payers)]

        # Distribute grand_total roughly equally to create raw totals.
        n = n_non_payers + 1
        base = grand_total // n
        raw_totals: dict = dict.fromkeys(non_payer_ids, base)
        raw_totals[payer_id] = grand_total - sum(raw_totals.values())

        result = RoundingPolicy.apply(raw_totals, grand_total, payer_id)
        assert sum(result.values()) == grand_total

    @given(
        grand_total=st.integers(min_value=0, max_value=100_000_000),
        n_non_payers=st.integers(min_value=1, max_value=19),
    )
    @settings(max_examples=10_000, suppress_health_check=[HealthCheck.too_slow])
    def test_payer_non_negative(self, grand_total: int, n_non_payers: int):
        """Amendment SE-2: Payer total is never negative after rounding."""
        payer_id = uuid4()
        non_payer_ids = [uuid4() for _ in range(n_non_payers)]

        n = n_non_payers + 1
        base = grand_total // n
        raw_totals: dict = dict.fromkeys(non_payer_ids, base)
        raw_totals[payer_id] = grand_total - sum(raw_totals.values())

        result = RoundingPolicy.apply(raw_totals, grand_total, payer_id)
        assert result[payer_id] >= 0


# ── SplitCalculator properties (equal mode) ─────────────────────────────────

@pytest.mark.unit
class TestSplitCalculatorEqualProperties:
    @given(
        subtotal=_paise_amount(),
        n=_participant_count(),
        tax=st.integers(min_value=0, max_value=1_000_000),
        discount=st.integers(min_value=0, max_value=1_000_000),
        delivery=st.integers(min_value=0, max_value=500_000),
    )
    @settings(max_examples=10_000, suppress_health_check=[HealthCheck.too_slow])
    def test_sum_conservation_equal(
        self, subtotal: int, n: int, tax: int, discount: int, delivery: int,
    ):
        """For any valid equal split input, sum(totals) == grand_total."""
        participants = [
            SplitParticipant(id=uuid4(), is_payer=(i == 0), join_order=i)
            for i in range(n)
        ]
        result = SplitCalculator.calculate(SplitInput(
            mode="equal",
            items=[SplitItem(id=uuid4(), quantity=1, total_paise=subtotal)],
            assignments=[],
            adjustments=[
                SplitAdjustment(type="tax", amount_paise=tax, allocation="proportional"),
                SplitAdjustment(type="discount", amount_paise=discount, allocation="proportional"),
                SplitAdjustment(type="delivery_fee", amount_paise=delivery, allocation="equal"),
            ],
            participants=participants,
        ))
        assert sum(t.total_paise for t in result.participant_totals) == result.grand_total_paise
        assert result.invariant_holds is True

    @given(
        subtotal=_paise_amount(),
        n=_participant_count(),
    )
    @settings(max_examples=5_000, suppress_health_check=[HealthCheck.too_slow])
    def test_non_negative_totals_equal(self, subtotal: int, n: int):
        """All participant totals are non-negative in equal mode."""
        participants = [
            SplitParticipant(id=uuid4(), is_payer=(i == 0), join_order=i)
            for i in range(n)
        ]
        result = SplitCalculator.calculate(SplitInput(
            mode="equal",
            items=[SplitItem(id=uuid4(), quantity=1, total_paise=subtotal)],
            assignments=[],
            adjustments=[],
            participants=participants,
        ))
        assert all(t.total_paise >= 0 for t in result.participant_totals)

    @given(
        subtotal=_paise_amount(),
        n=_participant_count(),
    )
    @settings(max_examples=5_000, suppress_health_check=[HealthCheck.too_slow])
    def test_payer_non_negative_equal(self, subtotal: int, n: int):
        """Payer total is always >= 0."""
        participants = [
            SplitParticipant(id=uuid4(), is_payer=(i == 0), join_order=i)
            for i in range(n)
        ]
        result = SplitCalculator.calculate(SplitInput(
            mode="equal",
            items=[SplitItem(id=uuid4(), quantity=1, total_paise=subtotal)],
            assignments=[],
            adjustments=[],
            participants=participants,
        ))
        payer_total = next(t for t in result.participant_totals if t.is_payer)
        assert payer_total.total_paise >= 0

    @given(
        subtotal=_paise_amount(),
        n=_participant_count(),
    )
    @settings(max_examples=1_000, suppress_health_check=[HealthCheck.too_slow])
    def test_determinism_equal(self, subtotal: int, n: int):
        """Same input always produces same output."""
        participants = [
            SplitParticipant(id=uuid4(), is_payer=(i == 0), join_order=i)
            for i in range(n)
        ]
        inp = SplitInput(
            mode="equal",
            items=[SplitItem(id=uuid4(), quantity=1, total_paise=subtotal)],
            assignments=[],
            adjustments=[],
            participants=participants,
        )
        r1 = SplitCalculator.calculate(inp)
        r2 = SplitCalculator.calculate(inp)
        for t1, t2 in zip(r1.participant_totals, r2.participant_totals, strict=False):
            assert t1.total_paise == t2.total_paise


# ── SplitCalculator properties (item-wise mode) ─────────────────────────────

@pytest.mark.unit
class TestSplitCalculatorItemWiseProperties:
    @given(
        n=_participant_count(),
        n_items=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=5_000, suppress_health_check=[HealthCheck.too_slow])
    def test_sum_conservation_item_wise(self, n: int, n_items: int):
        """Sum conservation holds for random item-wise splits."""
        participants = [
            SplitParticipant(id=uuid4(), is_payer=(i == 0), join_order=i)
            for i in range(n)
        ]

        items = []
        assignments = []
        for _ in range(n_items):
            qty = 1  # Keep simple: 1 unit per item
            total = (uuid4().int % 10000) + 1  # 1-10000 paise
            item = SplitItem(id=uuid4(), quantity=qty, total_paise=total)
            items.append(item)
            # Assign to a random participant
            assignee_idx = uuid4().int % n
            assignments.append(SplitAssignment(
                item_id=item.id,
                participant_id=participants[assignee_idx].id,
                claimed_qty=qty,
                created_at=datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC),
            ))

        result = SplitCalculator.calculate(SplitInput(
            mode="item_wise",
            items=items,
            assignments=assignments,
            adjustments=[],
            participants=participants,
        ))
        assert sum(t.total_paise for t in result.participant_totals) == result.grand_total_paise
        assert result.invariant_holds is True
        assert all(t.total_paise >= 0 for t in result.participant_totals)
