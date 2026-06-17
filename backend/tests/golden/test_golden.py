"""
Golden fixture test runner.

Loads JSON fixtures from tests/golden/ and runs them through the
SplitCalculator to verify invariant correctness against real-world
receipt scenarios.

Each fixture specifies:
  - input: A SplitInput in JSON form (with string IDs)
  - expected: What to verify (grand_total, sum conservation, etc.)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest

from app.split.calculator import SplitCalculator
from app.split.models import (
    SplitAdjustment,
    SplitAssignment,
    SplitInput,
    SplitItem,
    SplitParticipant,
)


# Deterministic UUID generation from string IDs in fixtures.
def _to_uuid(s: str) -> UUID:
    return uuid5(NAMESPACE_DNS, s)


def _load_fixtures() -> list[tuple[str, dict]]:
    """Load all JSON fixtures from the golden directory."""
    golden_dir = Path(__file__).parent
    fixtures = []
    for f in sorted(golden_dir.glob("*.json")):
        with f.open() as fh:
            data = json.load(fh)
        fixtures.append((f.stem, data))
    return fixtures


def _build_split_input(data: dict) -> SplitInput:
    """Convert a JSON fixture's input to a SplitInput."""
    inp = data["input"]

    participants = [
        SplitParticipant(
            id=_to_uuid(p["id"]),
            is_payer=p["is_payer"],
            join_order=p["join_order"],
        )
        for p in inp["participants"]
    ]

    items = [
        SplitItem(
            id=_to_uuid(i["id"]),
            quantity=i["quantity"],
            total_paise=i["total_paise"],
        )
        for i in inp["items"]
    ]

    assignments = [
        SplitAssignment(
            item_id=_to_uuid(a["item_id"]),
            participant_id=_to_uuid(a["participant_id"]),
            claimed_qty=a["claimed_qty"],
            created_at=datetime.fromisoformat(a["created_at"]).replace(tzinfo=UTC)
            if isinstance(a["created_at"], str) else a["created_at"],
        )
        for a in inp.get("assignments", [])
    ]

    adjustments = [
        SplitAdjustment(
            type=a["type"],
            amount_paise=a["amount_paise"],
            allocation=a["allocation"],
        )
        for a in inp.get("adjustments", [])
    ]

    return SplitInput(
        mode=inp["mode"],
        items=items,
        assignments=assignments,
        adjustments=adjustments,
        participants=participants,
    )


# ── Parametrized test ────────────────────────────────────────────────────────

_FIXTURES = _load_fixtures()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fixture_name", "fixture_data"),
    _FIXTURES,
    ids=[f[0] for f in _FIXTURES],
)
class TestGoldenFixtures:
    def test_sum_conservation(self, fixture_name: str, fixture_data: dict):
        """sum(participant_totals) == grand_total_paise."""
        inp = _build_split_input(fixture_data)
        result = SplitCalculator.calculate(inp)

        expected = fixture_data["expected"]
        if expected.get("sum_conservation", True):
            assert sum(t.total_paise for t in result.participant_totals) == result.grand_total_paise

    def test_grand_total(self, fixture_name: str, fixture_data: dict):
        """Grand total matches expected."""
        inp = _build_split_input(fixture_data)
        result = SplitCalculator.calculate(inp)

        expected = fixture_data["expected"]
        if "grand_total_paise" in expected:
            assert result.grand_total_paise == expected["grand_total_paise"], (
                f"Fixture '{fixture_name}': expected grand_total={expected['grand_total_paise']}, "
                f"got {result.grand_total_paise}"
            )

    def test_all_non_negative(self, fixture_name: str, fixture_data: dict):
        """All participant totals are >= 0."""
        inp = _build_split_input(fixture_data)
        result = SplitCalculator.calculate(inp)

        expected = fixture_data["expected"]
        if expected.get("all_non_negative", True):
            for t in result.participant_totals:
                assert t.total_paise >= 0, (
                    f"Fixture '{fixture_name}': participant {t.participant_id} "
                    f"has negative total {t.total_paise}"
                )

    def test_participant_count(self, fixture_name: str, fixture_data: dict):
        """Correct number of participants in output."""
        inp = _build_split_input(fixture_data)
        result = SplitCalculator.calculate(inp)

        expected = fixture_data["expected"]
        if "participant_count" in expected:
            assert len(result.participant_totals) == expected["participant_count"]

    def test_item_shares(self, fixture_name: str, fixture_data: dict):
        """Per-participant item shares match expected values."""
        expected = fixture_data["expected"]
        if "item_shares" not in expected:
            pytest.skip("No item_shares in expected")

        inp = _build_split_input(fixture_data)
        result = SplitCalculator.calculate(inp)

        expected_shares = expected["item_shares"]
        for pid_str, expected_items_paise in expected_shares.items():
            pid = _to_uuid(pid_str)
            actual = next(
                (t for t in result.participant_totals if t.participant_id == pid),
                None,
            )
            assert actual is not None, f"Participant {pid_str} not in result"
            assert actual.items_paise == expected_items_paise, (
                f"Fixture '{fixture_name}': {pid_str} expected items_paise="
                f"{expected_items_paise}, got {actual.items_paise}"
            )

    def test_invariant_holds(self, fixture_name: str, fixture_data: dict):
        """invariant_holds flag is True."""
        inp = _build_split_input(fixture_data)
        result = SplitCalculator.calculate(inp)
        assert result.invariant_holds is True
