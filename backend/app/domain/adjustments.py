from __future__ import annotations

ADDITIVE_ADJUSTMENT_TYPES = {
    "tax",
    "service_charge",
    "delivery_fee",
    "packaging_fee",
    "tip",
}
SUBTRACTIVE_ADJUSTMENT_TYPES = {"discount", "coupon", "offer"}
SIGNED_ADJUSTMENT_TYPES = {"adjustment", "rounding"}
ADJUSTMENT_TYPES = ADDITIVE_ADJUSTMENT_TYPES | SUBTRACTIVE_ADJUSTMENT_TYPES | SIGNED_ADJUSTMENT_TYPES

CALCULATION_TYPE_BY_ADJUSTMENT_TYPE = {
    "tax": "tax",
    "service_charge": "service_charge",
    "delivery_fee": "delivery_fee",
    "packaging_fee": "service_charge",
    "tip": "service_charge",
    "discount": "discount",
    "coupon": "discount",
    "offer": "discount",
    "adjustment": "adjustment",
    "rounding": "adjustment",
}


def normalize_stored_amount(adjustment_type: str, amount_paise: int) -> int:
    if adjustment_type in ADDITIVE_ADJUSTMENT_TYPES | SUBTRACTIVE_ADJUSTMENT_TYPES:
        return abs(amount_paise)
    return amount_paise


def calculation_type(adjustment_type: str) -> str:
    return CALCULATION_TYPE_BY_ADJUSTMENT_TYPE[adjustment_type]


def is_percentage_allowed(adjustment_type: str) -> bool:
    return adjustment_type != "rounding"

