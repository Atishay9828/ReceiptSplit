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
        "sample_restaurant_expected",
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
    expected["items"] = [
        {key: value for key, value in item.items() if key != "confidence"}
        for item in expected["items"]
    ]

    actual = parsed.model_dump(
        mode="json",
        include={
            "merchant_name",
            "subtotal_paise",
            "tax_paise",
            "discount_paise",
            "total_paise",
            "items",
            "adjustments",
            "warnings",
            "needs_review",
        },
        exclude={"items": {"__all__": {"confidence"}}},
    )
    actual["adjustments"] = [
        {"type": adjustment["type"], "amount_paise": adjustment["amount_paise"]}
        for adjustment in actual["adjustments"]
    ]

    assert actual == expected


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


def test_parser_handles_rupee_symbol_and_x_quantity_line_totals_conservatively() -> None:
    parser = IndianRestaurantReceiptParser()
    parsed = parser.parse(
        """SAMPLE RESTAURANT
123 Test Street
Date: 01/01/2024
Butter Chicken x1 ₹350.00
Garlic Naan x2 ₹120.00
Dal Tadka x1 ₹180.00
Lassi x2 ₹100.00
Subtotal: ₹750.00
Tax (5%): ₹37.50
Total: ₹787.50"""
    )

    assert [(item.name, item.quantity, item.total_paise) for item in parsed.items] == [
        ("Butter Chicken", 1, 35000),
        ("Garlic Naan", 2, 12000),
        ("Dal Tadka", 1, 18000),
        ("Lassi", 2, 10000),
    ]
    assert parsed.tax_paise == 3750
    assert parsed.total_paise == 78750
    assert "quantity_total_inferred" in parsed.warnings
    assert parsed.needs_review is True


def test_parser_keeps_rounding_as_a_signed_adjustment() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "URBAN THALI\nTea 240.00\nDiscount -20.00\nRounding -0.50\nGrand Total 219.50"
    )

    assert [(adjustment.type, adjustment.amount_paise) for adjustment in parsed.adjustments] == [
        ("discount", -2000),
        ("rounding", -50),
    ]
    assert parsed.needs_review is False


def test_parser_does_not_convert_percentage_only_tax_into_money() -> None:
    parsed = IndianRestaurantReceiptParser().parse("CAFE\nTea 200.00\nCGST 2.5%\nTotal 200.00")

    assert parsed.adjustments == []
    assert parsed.tax_paise is None
    assert "unresolved_adjustment_amount" in parsed.warnings
    assert parsed.needs_review is True


def test_parser_leaves_ocr_currency_glyph_tax_ambiguous() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "RIVERSIDE BISTRO\nSoup 8.50\nSubtotal 8.50\nTax R59\nService Charge 24.39\nGrand Total 173.48"
    )

    assert parsed.tax_paise is None
    assert not any(adjustment.type == "tax" for adjustment in parsed.adjustments)
    assert "unresolved_adjustment_amount" in parsed.warnings
    assert parsed.needs_review is True


def test_parser_prefers_printed_tax_amount_after_percentage() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "SPICE ROOM\nPaneer Tikka 250.00\nCGST 2.5% 8.50\nSGST 2.5% 8.50\nTotal 267.00"
    )

    assert parsed.tax_paise == 1700
    assert [adjustment.amount_paise for adjustment in parsed.adjustments] == [850, 850]


def test_parser_deduplicates_aggregate_tax_summary() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "CAFE\nTea 200.00\nCGST 2.50\nSGST 2.50\nTotal Tax 5.00\nGrand Total 205.00"
    )

    assert parsed.tax_paise == 500
    assert sum(adj.amount_paise for adj in parsed.adjustments) == 500
    assert "tax_summary_mismatch" not in parsed.warnings


def test_parser_keeps_service_charge_separate_from_tax() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "CAFE\nTea 100.00\nService Charge (18%) 18.00\nGrand Total 118.00"
    )

    assert parsed.tax_paise is None
    assert [(adj.type, adj.amount_paise) for adj in parsed.adjustments] == [
        ("service_charge", 1800)
    ]
    assert "service_charge_detected" in parsed.warnings


def test_parser_reads_leading_quantity_and_decimal_comma() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "RIVERSIDE BISTRO\n1 Burrata Salad 14,00\n2 Seared Scallops 36,00"
    )

    assert [(item.name, item.quantity, item.total_paise) for item in parsed.items] == [
        ("Burrata Salad", 1, 1400),
        ("Seared Scallops", 2, 3600),
    ]


def test_parser_reads_quantity_unit_and_printed_line_total() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "BIRYANI HOUSE\n2 Chicken Biryani 180.00 360.00"
    )

    assert len(parsed.items) == 1
    assert parsed.items[0].name == "Chicken Biryani"
    assert parsed.items[0].quantity == 2
    assert parsed.items[0].unit_price_paise == 18000
    assert parsed.items[0].total_paise == 36000


def test_parser_excludes_order_metadata_from_items() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "BISTRO\n18 Riverwalk Drive\nOrder #: 0427\nTable: 12\nTea 10.00\nPaid in Full"
    )

    assert [(item.name, item.total_paise) for item in parsed.items] == [("Tea", 1000)]


def test_parser_preserves_unicode_item_names_and_removes_leading_ocr_punctuation() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "RIVERSIDE BISTRO\n{1 Sautéed Green Beans 6.50\nGrand Total 6.50"
    )

    assert [(item.name, item.quantity, item.total_paise) for item in parsed.items] == [
        ("Sautéed Green Beans", 1, 650)
    ]


def test_parser_flags_out_of_range_ocr_amount_without_raising() -> None:
    parsed = IndianRestaurantReceiptParser().parse(
        "CAFE\nSuspicious Item 999999999.00\nGrand Total 999999999.00"
    )

    assert parsed.items == []
    assert parsed.total_paise is None
    assert parsed.needs_review is True
    assert "invalid_item_amount" in parsed.warnings
    assert "invalid_total_amount" in parsed.warnings
