"""
Tests for app.split.invariants.

Verifies that invariant checks correctly detect violations and
correctly pass on valid results.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.split.exceptions import (
    AllocationConservationViolation,
    NegativePayerTotalViolation,
    NegativeTotalViolation,
    SumConservationViolation,
)
from app.split.invariants import (
    check_all_invariants,
    check_allocation_conservation,
    check_non_negative_totals,
    check_payer_non_negative,
    check_sum_conservation,
)
from app.split.models import ParticipantBreakdown, SplitResult


def _breakdown(pid=None, total_paise=0, is_payer=False, **kwargs):
    return ParticipantBreakdown(
        participant_id=pid or uuid4(),
        items_paise=kwargs.get("items_paise", 0),
        discount_paise=kwargs.get("discount_paise", 0),
        tax_paise=kwargs.get("tax_paise", 0),
        service_charge_paise=kwargs.get("service_charge_paise", 0),
        delivery_fee_paise=kwargs.get("delivery_fee_paise", 0),
        adjustment_paise=kwargs.get("adjustment_paise", 0),
        total_paise=total_paise,
        is_payer=is_payer,
    )


@pytest.mark.unit
class TestSumConservation:
    def test_passes_on_correct_sum(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=600, is_payer=True),
                _breakdown(total_paise=400),
            ],
            invariant_holds=True,
        )
        check_sum_conservation(result)  # Should not raise.

    def test_fails_on_incorrect_sum(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=600, is_payer=True),
                _breakdown(total_paise=500),  # Sum = 1100 != 1000
            ],
            invariant_holds=True,
        )
        with pytest.raises(SumConservationViolation):
            check_sum_conservation(result)

    def test_fails_on_deficit(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=400, is_payer=True),
                _breakdown(total_paise=400),  # Sum = 800 != 1000
            ],
            invariant_holds=True,
        )
        with pytest.raises(SumConservationViolation):
            check_sum_conservation(result)


@pytest.mark.unit
class TestNonNegativeTotals:
    def test_passes_on_all_positive(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=600, is_payer=True),
                _breakdown(total_paise=400),
            ],
            invariant_holds=True,
        )
        check_non_negative_totals(result)  # Should not raise.

    def test_passes_on_zero(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=1000, is_payer=True),
                _breakdown(total_paise=0),  # Zero is valid
            ],
            invariant_holds=True,
        )
        check_non_negative_totals(result)

    def test_fails_on_negative(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=1100, is_payer=True),
                _breakdown(total_paise=-100),
            ],
            invariant_holds=True,
        )
        with pytest.raises(NegativeTotalViolation):
            check_non_negative_totals(result)


@pytest.mark.unit
class TestPayerNonNegative:
    def test_passes_on_positive_payer(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=600, is_payer=True),
                _breakdown(total_paise=400),
            ],
            invariant_holds=True,
        )
        check_payer_non_negative(result)

    def test_passes_on_zero_payer(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=0, is_payer=True),
                _breakdown(total_paise=1000),
            ],
            invariant_holds=True,
        )
        check_payer_non_negative(result)

    def test_fails_on_negative_payer(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=-100, is_payer=True),
                _breakdown(total_paise=1100),
            ],
            invariant_holds=True,
        )
        with pytest.raises(NegativePayerTotalViolation):
            check_payer_non_negative(result)


@pytest.mark.unit
class TestAllocationConservation:
    def test_passes_on_exact_match(self):
        alloc = {uuid4(): 300, uuid4(): 200, uuid4(): 500}
        check_allocation_conservation(alloc, 1000, "tax")

    def test_fails_on_mismatch(self):
        alloc = {uuid4(): 300, uuid4(): 200, uuid4(): 499}
        with pytest.raises(AllocationConservationViolation):
            check_allocation_conservation(alloc, 1000, "tax")


@pytest.mark.unit
class TestCheckAllInvariants:
    def test_passes_valid_result(self):
        payer_id = uuid4()
        other_id = uuid4()
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(pid=payer_id, total_paise=600, is_payer=True),
                _breakdown(pid=other_id, total_paise=400),
            ],
            invariant_holds=True,
        )
        check_all_invariants(result)

    def test_fails_on_sum_violation(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=600, is_payer=True),
                _breakdown(total_paise=500),
            ],
            invariant_holds=True,
        )
        with pytest.raises(SumConservationViolation):
            check_all_invariants(result)

    def test_fails_on_negative_total(self):
        result = SplitResult(
            grand_total_paise=1000,
            participant_totals=[
                _breakdown(total_paise=1100, is_payer=True),
                _breakdown(total_paise=-100),
            ],
            invariant_holds=True,
        )
        # Will fail on sum check first (1100 + -100 = 1000), then negative total.
        # Actually 1100 + (-100) = 1000, so sum check passes.
        with pytest.raises(NegativeTotalViolation):
            check_all_invariants(result)
