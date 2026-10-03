from __future__ import annotations

from app.ocr.contracts import ParsedReceiptAdjustment, ParsedReceiptDraft, ParsedReceiptLine
from app.ocr.review import reconcile_warnings, review_values


def draft() -> ParsedReceiptDraft:
    return ParsedReceiptDraft(
        subtotal_paise=24000,
        total_paise=22050,
        items=[
            ParsedReceiptLine(name="Tea", quantity=1, total_paise=24000),
        ],
        adjustments=[
            ParsedReceiptAdjustment(type="discount", label="Discount", amount_paise=-2000),
            ParsedReceiptAdjustment(type="rounding", label="Rounding", amount_paise=50),
        ],
    )


def test_review_total_applies_domain_sign_rules_and_signed_rounding() -> None:
    calculated, difference, fingerprint = review_values(draft())

    assert calculated == 22050
    assert difference == 0
    assert len(fingerprint) == 64


def test_review_fingerprint_changes_with_total_or_adjustments() -> None:
    initial = draft()
    changed = draft()
    changed.adjustments[1].amount_paise = -50

    assert review_values(initial)[2] != review_values(changed)[2]


def test_reconciliation_recomputes_stale_sum_warnings() -> None:
    parsed = draft()
    parsed.adjustments[1].amount_paise = -50
    parsed.total_paise = 21950

    warnings, needs_review = reconcile_warnings(
        [item.model_dump() for item in parsed.items],
        [adjustment.model_dump() for adjustment in parsed.adjustments],
        parsed.subtotal_paise,
        parsed.total_paise,
        ["items_sum_mismatch", "discount_detected"],
    )

    assert warnings == ["discount_detected"]
    assert needs_review is False


def test_review_missing_receipt_total_has_no_numeric_difference() -> None:
    parsed = draft()
    parsed.total_paise = None

    calculated, difference, _ = review_values(parsed)

    assert calculated == 22050
    assert difference is None
