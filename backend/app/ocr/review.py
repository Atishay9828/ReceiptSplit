from __future__ import annotations

import hashlib
import json
from typing import Any

from app.domain.adjustments import ADDITIVE_ADJUSTMENT_TYPES, SUBTRACTIVE_ADJUSTMENT_TYPES

AMOUNT_REVIEW_WARNINGS = {
    "items_sum_mismatch",
    "items_subtotal_mismatch",
    "missing_total",
    "unresolved_adjustment_amount",
}
NEEDS_REVIEW_WARNINGS = AMOUNT_REVIEW_WARNINGS | {
    "ambiguous_line",
    "low_confidence_line",
    "quantity_total_inferred",
    "quantity_price_mismatch",
    "tax_summary_mismatch",
    "invalid_item_amount",
    "invalid_total_amount",
}


def review_values(draft: Any) -> tuple[int, int | None, str]:
    items = [dict(item) for item in draft.items]
    adjustments = [dict(adjustment) for adjustment in draft.adjustments]
    item_subtotal = sum(int(item["total_paise"]) for item in items)
    calculated_total = item_subtotal + sum(
        _signed_amount(str(adjustment["type"]), int(adjustment["amount_paise"]))
        for adjustment in adjustments
    )
    difference = (
        calculated_total - int(draft.total_paise) if draft.total_paise is not None else None
    )
    canonical = {
        "merchant_name": draft.merchant_name,
        "subtotal_paise": draft.subtotal_paise,
        "total_paise": draft.total_paise,
        "items": items,
        "adjustments": adjustments,
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return calculated_total, difference, fingerprint


def reconcile_warnings(
    items: list[dict[str, Any]],
    adjustments: list[dict[str, Any]],
    subtotal_paise: int | None,
    total_paise: int | None,
    existing_warnings: list[str],
) -> tuple[list[str], bool]:
    warnings = [warning for warning in existing_warnings if warning not in AMOUNT_REVIEW_WARNINGS]
    item_subtotal = sum(int(item["total_paise"]) for item in items)
    calculated_total = item_subtotal + sum(
        _signed_amount(str(adjustment["type"]), int(adjustment["amount_paise"]))
        for adjustment in adjustments
    )
    if subtotal_paise is not None and item_subtotal != subtotal_paise:
        warnings.append("items_subtotal_mismatch")
    if total_paise is None:
        warnings.append("missing_total")
    elif items and calculated_total != total_paise:
        warnings.append("items_sum_mismatch")
    needs_review = not items or any(warning in NEEDS_REVIEW_WARNINGS for warning in warnings)
    return warnings, needs_review


def _signed_amount(adjustment_type: str, amount_paise: int) -> int:
    if adjustment_type in ADDITIVE_ADJUSTMENT_TYPES:
        return abs(amount_paise)
    if adjustment_type in SUBTRACTIVE_ADJUSTMENT_TYPES:
        return -abs(amount_paise)
    return amount_paise
