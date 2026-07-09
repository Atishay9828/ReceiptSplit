"""
Tests for SplitCalculator.

The full 13-step pipeline tested end-to-end.

Covers:
  - Equal split (simple, with taxes, with discounts, with all adjustments)
  - Item-wise split (full claims, shared items, per-item remainder)
  - Discount capping (PDD E6)
  - Zero-price items (PDD E5)
  - Zero grand total (PDD E7)
  - Rounding behavior
  - Input validation
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.split.calculator import SplitCalculator
from app.split.models import (
    SplitAdjustment,
    SplitAssignment,
    SplitInput,
    SplitItem,
    SplitParticipant,
)


def _ts(i: int = 0) -> datetime:
    """Deterministic timestamps for claims."""
    return datetime(2026, 6, 1, 12, 0, i, tzinfo=UTC)


def _participants(n: int):
    """Create n participants where first is payer."""
    return [SplitParticipant(id=uuid4(), is_payer=(i == 0), join_order=i) for i in range(n)]


@pytest.mark.unit
class TestEqualSplit:
    def test_simple_equal_2_people(self):
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=1000)],
                assignments=[],
                adjustments=[],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 1000
        assert result.invariant_holds is True
        assert sum(t.total_paise for t in result.participant_totals) == 1000
        # 1000 / 2 = 500 each (round to ₹5 each)
        for t in result.participant_totals:
            assert t.total_paise == 500

    def test_simple_equal_3_people_odd_amount(self):
        ps = _participants(3)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=1000)],
                assignments=[],
                adjustments=[],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 1000
        assert sum(t.total_paise for t in result.participant_totals) == 1000

    def test_equal_with_tax(self):
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=10000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(type="tax", amount_paise=1800, allocation="proportional"),
                ],
                participants=ps,
            )
        )
        # Grand total = 10000 + 1800 = 11800
        assert result.grand_total_paise == 11800
        assert sum(t.total_paise for t in result.participant_totals) == 11800

    def test_equal_with_discount(self):
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=10000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(type="discount", amount_paise=2000, allocation="proportional"),
                ],
                participants=ps,
            )
        )
        # Grand total = 10000 - 2000 = 8000
        assert result.grand_total_paise == 8000
        assert sum(t.total_paise for t in result.participant_totals) == 8000

    def test_equal_with_negative_discount_is_still_subtractive(self):
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=50000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(type="discount", amount_paise=-10000, allocation="proportional"),
                ],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 40000
        assert sum(t.total_paise for t in result.participant_totals) == 40000

    def test_equal_with_percentage_tax(self):
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=50000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(
                        type="tax",
                        amount_paise=0,
                        allocation="proportional",
                        rate_basis_points=500,
                    ),
                ],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 52500

    def test_equal_with_percentage_discount(self):
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=50000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(
                        type="discount",
                        amount_paise=0,
                        allocation="proportional",
                        rate_basis_points=1000,
                    ),
                ],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 45000

    def test_equal_with_percentage_tax_and_discount_uses_current_pipeline(self):
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=50000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(
                        type="tax",
                        amount_paise=0,
                        allocation="proportional",
                        rate_basis_points=500,
                    ),
                    SplitAdjustment(
                        type="discount",
                        amount_paise=0,
                        allocation="proportional",
                        rate_basis_points=1000,
                    ),
                ],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 47500

    def test_equal_with_all_adjustment_types(self):
        ps = _participants(3)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=30000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(type="discount", amount_paise=3000, allocation="proportional"),
                    SplitAdjustment(type="tax", amount_paise=4860, allocation="proportional"),
                    SplitAdjustment(
                        type="service_charge", amount_paise=2700, allocation="proportional"
                    ),
                    SplitAdjustment(type="delivery_fee", amount_paise=5000, allocation="equal"),
                ],
                participants=ps,
            )
        )
        # Grand = 30000 - 3000 + 4860 + 2700 + 5000 = 39560
        assert result.grand_total_paise == 39560
        assert sum(t.total_paise for t in result.participant_totals) == 39560
        # Verify each participant has non-negative total
        for t in result.participant_totals:
            assert t.total_paise >= 0

    def test_equal_with_delivery_fee_equal_allocation(self):
        """Delivery fee uses equal allocation, not proportional."""
        ps = _participants(3)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=9000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(type="delivery_fee", amount_paise=300, allocation="equal"),
                ],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 9300
        # Delivery fee: 300 / 3 = 100 each
        for t in result.participant_totals:
            assert t.delivery_fee_paise == 100

    def test_equal_with_multiple_items(self):
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[
                    SplitItem(id=uuid4(), quantity=1, total_paise=5000),
                    SplitItem(id=uuid4(), quantity=2, total_paise=3000),
                    SplitItem(id=uuid4(), quantity=1, total_paise=2000),
                ],
                assignments=[],
                adjustments=[],
                participants=ps,
            )
        )
        # Subtotal = 5000 + 3000 + 2000 = 10000
        assert result.grand_total_paise == 10000
        assert sum(t.total_paise for t in result.participant_totals) == 10000


@pytest.mark.unit
class TestItemWiseSplit:
    def test_simple_item_wise_2_items_2_people(self):
        ps = _participants(2)
        item1 = SplitItem(id=uuid4(), quantity=1, total_paise=600)
        item2 = SplitItem(id=uuid4(), quantity=1, total_paise=400)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="item_wise",
                items=[item1, item2],
                assignments=[
                    SplitAssignment(
                        item_id=item1.id, participant_id=ps[0].id, claimed_qty=1, created_at=_ts(0)
                    ),
                    SplitAssignment(
                        item_id=item2.id, participant_id=ps[1].id, claimed_qty=1, created_at=_ts(1)
                    ),
                ],
                adjustments=[],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 1000
        assert sum(t.total_paise for t in result.participant_totals) == 1000

    def test_item_wise_shared_item(self):
        """Two participants share a 3-quantity item."""
        ps = _participants(2)
        item = SplitItem(id=uuid4(), quantity=3, total_paise=900)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="item_wise",
                items=[item],
                assignments=[
                    SplitAssignment(
                        item_id=item.id, participant_id=ps[0].id, claimed_qty=2, created_at=_ts(0)
                    ),
                    SplitAssignment(
                        item_id=item.id, participant_id=ps[1].id, claimed_qty=1, created_at=_ts(1)
                    ),
                ],
                adjustments=[],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 900
        # unit_cost = 900 // 3 = 300
        # ps[0] items: 300 * 2 = 600
        # ps[1] items: 300 * 1 = 300
        # remainder = 900 - 300*3 = 0
        assert sum(t.total_paise for t in result.participant_totals) == 900

    def test_item_wise_per_item_remainder_to_last_claimer(self):
        """Per-item remainder goes to the last claimer by timestamp."""
        ps = _participants(2)
        # 10 paise / 3 quantity => unit_cost = 3, remainder = 1
        item = SplitItem(id=uuid4(), quantity=3, total_paise=10)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="item_wise",
                items=[item],
                assignments=[
                    SplitAssignment(
                        item_id=item.id,
                        participant_id=ps[0].id,
                        claimed_qty=2,
                        created_at=_ts(0),
                    ),
                    SplitAssignment(
                        item_id=item.id,
                        participant_id=ps[1].id,
                        claimed_qty=1,
                        created_at=_ts(1),  # later => last claimer
                    ),
                ],
                adjustments=[],
                participants=ps,
            )
        )
        # unit_cost = 10 // 3 = 3
        # ps[0] items: 3 * 2 = 6
        # ps[1] items: 3 * 1 = 3, + 1 remainder = 4
        totals = {t.participant_id: t for t in result.participant_totals}
        assert totals[ps[0].id].items_paise == 6
        assert totals[ps[1].id].items_paise == 4
        assert result.grand_total_paise == 10

    def test_item_wise_with_taxes(self):
        ps = _participants(2)
        item1 = SplitItem(id=uuid4(), quantity=1, total_paise=6000)
        item2 = SplitItem(id=uuid4(), quantity=1, total_paise=4000)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="item_wise",
                items=[item1, item2],
                assignments=[
                    SplitAssignment(
                        item_id=item1.id, participant_id=ps[0].id, claimed_qty=1, created_at=_ts(0)
                    ),
                    SplitAssignment(
                        item_id=item2.id, participant_id=ps[1].id, claimed_qty=1, created_at=_ts(1)
                    ),
                ],
                adjustments=[
                    SplitAdjustment(type="tax", amount_paise=1800, allocation="proportional"),
                ],
                participants=ps,
            )
        )
        # Grand = 10000 + 1800 = 11800
        assert result.grand_total_paise == 11800
        assert sum(t.total_paise for t in result.participant_totals) == 11800

    def test_item_wise_creator_claims(self):
        """PDD: Creator can claim items (reduces their receive amount)."""
        ps = _participants(2)
        item = SplitItem(id=uuid4(), quantity=2, total_paise=1000)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="item_wise",
                items=[item],
                assignments=[
                    SplitAssignment(
                        item_id=item.id, participant_id=ps[0].id, claimed_qty=1, created_at=_ts(0)
                    ),
                    SplitAssignment(
                        item_id=item.id, participant_id=ps[1].id, claimed_qty=1, created_at=_ts(1)
                    ),
                ],
                adjustments=[],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 1000
        assert sum(t.total_paise for t in result.participant_totals) == 1000


@pytest.mark.unit
class TestEdgeCases:
    def test_zero_price_item(self):
        """PDD E5: Zero-price item is valid, claims contribute ₹0."""
        ps = _participants(2)
        item = SplitItem(id=uuid4(), quantity=1, total_paise=0)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[item],
                assignments=[],
                adjustments=[],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 0
        assert all(t.total_paise == 0 for t in result.participant_totals)

    def test_zero_grand_total(self):
        """PDD E7: Grand total = ₹0. All totals = 0."""
        ps = _participants(3)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=0)],
                assignments=[],
                adjustments=[],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 0
        assert all(t.total_paise == 0 for t in result.participant_totals)

    def test_discount_exceeds_subtotal(self):
        """PDD E6: Discount > subtotal => capped at subtotal."""
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=1000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(type="discount", amount_paise=1500, allocation="proportional"),
                    SplitAdjustment(type="tax", amount_paise=180, allocation="proportional"),
                ],
                participants=ps,
            )
        )
        # Discount capped at subtotal (1000).
        # Grand = 1000 - 1000 + 180 = 180
        assert result.grand_total_paise == 180
        assert sum(t.total_paise for t in result.participant_totals) == 180

    def test_discount_equals_subtotal(self):
        """Full discount: post-discount = 0, taxes shared equally (SE-1 fallback)."""
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=1000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(type="discount", amount_paise=1000, allocation="proportional"),
                    SplitAdjustment(type="tax", amount_paise=200, allocation="proportional"),
                ],
                participants=ps,
            )
        )
        # Grand = 1000 - 1000 + 200 = 200
        assert result.grand_total_paise == 200
        assert sum(t.total_paise for t in result.participant_totals) == 200

    def test_1_paise_among_3(self):
        """PDD E9: 1 paise split among 3 people."""
        ps = _participants(3)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=1)],
                assignments=[],
                adjustments=[],
                participants=ps,
            )
        )
        assert result.grand_total_paise == 1
        assert sum(t.total_paise for t in result.participant_totals) == 1

    def test_multiple_taxes(self):
        """Multiple tax lines are summed and distributed together."""
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=10000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(
                        type="tax", amount_paise=250, allocation="proportional"
                    ),  # CGST
                    SplitAdjustment(
                        type="tax", amount_paise=250, allocation="proportional"
                    ),  # SGST
                ],
                participants=ps,
            )
        )
        # Grand = 10000 + 500 = 10500
        assert result.grand_total_paise == 10500
        assert sum(t.total_paise for t in result.participant_totals) == 10500

    def test_generic_adjustment_negative(self):
        """'adjustment' type can be negative (OCR reconciliation per DB-4)."""
        ps = _participants(2)
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=[SplitItem(id=uuid4(), quantity=1, total_paise=10000)],
                assignments=[],
                adjustments=[
                    SplitAdjustment(
                        type="adjustment", amount_paise=-200, allocation="proportional"
                    ),
                ],
                participants=ps,
            )
        )
        # Grand = 10000 + (-200) = 9800
        assert result.grand_total_paise == 9800
        assert sum(t.total_paise for t in result.participant_totals) == 9800

    def test_many_items_equal_split(self):
        """10 items equally split among 4 people."""
        ps = _participants(4)
        items = [SplitItem(id=uuid4(), quantity=1, total_paise=i * 100 + 50) for i in range(10)]
        result = SplitCalculator.calculate(
            SplitInput(
                mode="equal",
                items=items,
                assignments=[],
                adjustments=[],
                participants=ps,
            )
        )
        subtotal = sum(item.total_paise for item in items)
        assert result.grand_total_paise == subtotal
        assert sum(t.total_paise for t in result.participant_totals) == subtotal


@pytest.mark.unit
class TestInputValidation:
    def test_less_than_2_participants_raises(self):
        with pytest.raises(ValueError, match="2 participants"):
            SplitCalculator.calculate(
                SplitInput(
                    mode="equal",
                    items=[SplitItem(id=uuid4(), quantity=1, total_paise=1000)],
                    assignments=[],
                    adjustments=[],
                    participants=[SplitParticipant(id=uuid4(), is_payer=True, join_order=0)],
                )
            )

    def test_no_payer_raises(self):
        with pytest.raises(ValueError, match="payer"):
            SplitCalculator.calculate(
                SplitInput(
                    mode="equal",
                    items=[SplitItem(id=uuid4(), quantity=1, total_paise=1000)],
                    assignments=[],
                    adjustments=[],
                    participants=[
                        SplitParticipant(id=uuid4(), is_payer=False, join_order=0),
                        SplitParticipant(id=uuid4(), is_payer=False, join_order=1),
                    ],
                )
            )

    def test_two_payers_raises(self):
        with pytest.raises(ValueError, match="payer"):
            SplitCalculator.calculate(
                SplitInput(
                    mode="equal",
                    items=[SplitItem(id=uuid4(), quantity=1, total_paise=1000)],
                    assignments=[],
                    adjustments=[],
                    participants=[
                        SplitParticipant(id=uuid4(), is_payer=True, join_order=0),
                        SplitParticipant(id=uuid4(), is_payer=True, join_order=1),
                    ],
                )
            )

    def test_negative_item_total_raises(self):
        with pytest.raises(ValueError, match="negative"):
            SplitCalculator.calculate(
                SplitInput(
                    mode="equal",
                    items=[SplitItem(id=uuid4(), quantity=1, total_paise=-100)],
                    assignments=[],
                    adjustments=[],
                    participants=_participants(2),
                )
            )

    def test_zero_quantity_raises(self):
        with pytest.raises(ValueError, match="quantity"):
            SplitCalculator.calculate(
                SplitInput(
                    mode="equal",
                    items=[SplitItem(id=uuid4(), quantity=0, total_paise=100)],
                    assignments=[],
                    adjustments=[],
                    participants=_participants(2),
                )
            )

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            SplitCalculator.calculate(
                SplitInput(
                    mode="percentage",
                    items=[SplitItem(id=uuid4(), quantity=1, total_paise=100)],
                    assignments=[],
                    adjustments=[],
                    participants=_participants(2),
                )
            )

    def test_item_wise_not_fully_assigned_raises(self):
        ps = _participants(2)
        item = SplitItem(id=uuid4(), quantity=3, total_paise=900)
        from app.shared.errors import UnclaimedItemsExist

        with pytest.raises(UnclaimedItemsExist):
            SplitCalculator.calculate(
                SplitInput(
                    mode="item_wise",
                    items=[item],
                    assignments=[
                        SplitAssignment(
                            item_id=item.id,
                            participant_id=ps[0].id,
                            claimed_qty=2,
                            created_at=_ts(0),
                        ),
                        # Only 2 of 3 assigned
                    ],
                    adjustments=[],
                    participants=ps,
                )
            )

    def test_item_wise_over_assigned_raises(self):
        ps = _participants(2)
        item = SplitItem(id=uuid4(), quantity=2, total_paise=800)
        from app.shared.errors import UnclaimedItemsExist

        with pytest.raises(UnclaimedItemsExist):
            SplitCalculator.calculate(
                SplitInput(
                    mode="item_wise",
                    items=[item],
                    assignments=[
                        SplitAssignment(
                            item_id=item.id,
                            participant_id=ps[0].id,
                            claimed_qty=2,
                            created_at=_ts(0),
                        ),
                        SplitAssignment(
                            item_id=item.id,
                            participant_id=ps[1].id,
                            claimed_qty=1,
                            created_at=_ts(1),
                        ),
                        # 3 assigned for 2 quantity
                    ],
                    adjustments=[],
                    participants=ps,
                )
            )


@pytest.mark.unit
class TestDeterminism:
    def test_equal_split_is_deterministic(self):
        ps = _participants(5)
        inp = SplitInput(
            mode="equal",
            items=[SplitItem(id=uuid4(), quantity=1, total_paise=10001)],
            assignments=[],
            adjustments=[
                SplitAdjustment(type="tax", amount_paise=1800, allocation="proportional"),
                SplitAdjustment(type="discount", amount_paise=500, allocation="proportional"),
            ],
            participants=ps,
        )
        r1 = SplitCalculator.calculate(inp)
        r2 = SplitCalculator.calculate(inp)
        for t1, t2 in zip(r1.participant_totals, r2.participant_totals, strict=False):
            assert t1.total_paise == t2.total_paise
            assert t1.items_paise == t2.items_paise
            assert t1.tax_paise == t2.tax_paise

    def test_item_wise_is_deterministic(self):
        ps = _participants(3)
        items = [
            SplitItem(id=uuid4(), quantity=2, total_paise=700),
            SplitItem(id=uuid4(), quantity=1, total_paise=300),
        ]
        inp = SplitInput(
            mode="item_wise",
            items=items,
            assignments=[
                SplitAssignment(
                    item_id=items[0].id, participant_id=ps[0].id, claimed_qty=1, created_at=_ts(0)
                ),
                SplitAssignment(
                    item_id=items[0].id, participant_id=ps[1].id, claimed_qty=1, created_at=_ts(1)
                ),
                SplitAssignment(
                    item_id=items[1].id, participant_id=ps[2].id, claimed_qty=1, created_at=_ts(2)
                ),
            ],
            adjustments=[],
            participants=ps,
        )
        r1 = SplitCalculator.calculate(inp)
        r2 = SplitCalculator.calculate(inp)
        for t1, t2 in zip(r1.participant_totals, r2.participant_totals, strict=False):
            assert t1.total_paise == t2.total_paise
