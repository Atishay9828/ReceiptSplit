from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.ocr.parser import IndianRestaurantReceiptParser

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "receipts"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "simple_restaurant",
        "gst_cgst_sgst",
        "discount_rounding",
        "quantity_x_price",
        "noisy_footer",
        "bad_spacing",
    ],
)
def test_parser_fixture_outputs(fixture_name: str) -> None:
    parser = IndianRestaurantReceiptParser()
    parsed = parser.parse((FIXTURE_ROOT / f"{fixture_name}.txt").read_text(encoding="utf-8"))
    expected = json.loads(
        (FIXTURE_ROOT / "expected" / f"{fixture_name}.json").read_text(encoding="utf-8")
    )

    assert (
        parsed.model_dump(
            include={
                "merchant_name",
                "subtotal_paise",
                "tax_paise",
                "discount_paise",
                "total_paise",
                "items",
                "warnings",
                "needs_review",
            }
        )
        == expected
    )


def test_parser_marks_mismatch_as_needs_review() -> None:
    parser = IndianRestaurantReceiptParser()
    parsed = parser.parse("CAFE\nTea 50.00\nCoffee 60.00\nGrand Total 500.00")

    assert parsed.needs_review is True
    assert "items_sum_mismatch" in parsed.warnings


def test_parser_never_uses_float_money() -> None:
    parser = IndianRestaurantReceiptParser()
    parsed = parser.parse("CAFE\nTea 12.35\nGrand Total 12.35")

    assert parsed.total_paise == 1235
    assert parsed.items[0].total_paise == 1235
    assert isinstance(parsed.total_paise, int)
    assert isinstance(parsed.items[0].total_paise, int)
    assert isinstance(parsed.items[0].unit_price_paise, int | type(None))
    assert isinstance(parser._parse_money("12.35"), Decimal)
