"""
ReceiptSplit — Input Validators & Sanitizers

All user-supplied string input passes through this module before reaching
the domain layer.  Validation raises `DomainError` subclasses directly.

Functions here are pure (no I/O, no DB access) and are tested exhaustively
in tests/unit/test_validators.py.
"""

from __future__ import annotations

import re

import bleach

from app.shared.errors import (
    InvalidAdjustmentAmount,
    InvalidItemName,
    InvalidNickname,
    InvalidVPAFormat,
)
from app.shared.types import COLOR_PALETTE, VPA, Nickname, Paise

# ── Constants ──────────────────────────────────────────────────────────────────

_VPA_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$")

#: Adjustment types that must have non-negative amounts.
#: The 'adjustment' type may be negative (OCR reconciliation, Phase 3).
_NON_NEGATIVE_ADJ_TYPES: frozenset[str] = frozenset(
    {"tax", "service_charge", "delivery_fee", "discount"}
)

#: Allowed HTML tags in user input — none.  All HTML is stripped.
_ALLOWED_TAGS: list[str] = []
_ALLOWED_ATTRS: dict[str, list[str]] = {}


# ── String sanitization ───────────────────────────────────────────────────────

def strip_html(value: str) -> str:
    """
    Strips all HTML tags from a string using the bleach library.
    Null bytes are removed.  Result is stripped of leading/trailing whitespace.

    This is the canonical sanitizer for all user-supplied text fields
    (nicknames, item names, etc.).
    """
    cleaned = bleach.clean(value, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)
    return cleaned.replace("\x00", "").strip()


# ── Nickname validation ───────────────────────────────────────────────────────

def validate_nickname(raw: str) -> Nickname:
    """
    Sanitizes and validates a participant nickname.

    Pipeline:
      1. Strip HTML tags
      2. Remove null bytes
      3. Trim whitespace
      4. Enforce 1-30 char length

    Raises:
        InvalidNickname: if the sanitized string is empty or > 30 chars.
    """
    sanitized = strip_html(raw)
    if len(sanitized) < 1 or len(sanitized) > 30:
        raise InvalidNickname()
    return Nickname(sanitized)


# ── Item name validation ──────────────────────────────────────────────────────

def validate_item_name(raw: str) -> str:
    """
    Sanitizes and validates a line item name.

    Pipeline:
      1. Strip HTML tags
      2. Remove null bytes
      3. Trim whitespace
      4. Enforce 1-200 char length

    Raises:
        InvalidItemName: if the sanitized string is empty or > 200 chars.
    """
    sanitized = strip_html(raw)
    if len(sanitized) < 1 or len(sanitized) > 200:
        raise InvalidItemName()
    return sanitized


# ── VPA validation ────────────────────────────────────────────────────────────

def validate_vpa(raw: str) -> VPA:
    """
    Validates a UPI VPA string.

    No HTML stripping (VPA has no HTML relevance).
    Max 50 characters.  Regex: ^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$

    Raises:
        InvalidVPAFormat: if regex fails or length > 50.
    """
    value = raw.strip()
    if len(value) > 50 or not _VPA_PATTERN.match(value):
        raise InvalidVPAFormat()
    return VPA(value)


# ── Paise validation ──────────────────────────────────────────────────────────

def validate_paise(value: int, *, max_value: int, field_name: str = "amount") -> Paise:
    """
    Validates an integer paise amount.

    Args:
        value:      The raw integer value.
        max_value:  Upper bound (inclusive).
        field_name: Field name for error context.

    Raises:
        ValueError: if value < 0 or value > max_value.
    """
    if not isinstance(value, int) or value < 0 or value > max_value:
        raise ValueError(
            f"{field_name} must be an integer between 0 and {max_value}, got {value!r}"
        )
    return Paise(value)


# ── Adjustment amount validation ──────────────────────────────────────────────

def validate_adjustment_amount(adj_type: str, amount_paise: int) -> None:
    """
    Validates the amount_paise for a split adjustment.

    Non-negative enforcement (per DB-4 amendment):
      - 'tax', 'service_charge', 'delivery_fee', 'discount': must be >= 0
      - 'adjustment': may be negative (OCR reconciliation, Phase 3)

    Raises:
        InvalidAdjustmentAmount: if a non-adjustment type has amount < 0.
    """
    if adj_type in _NON_NEGATIVE_ADJ_TYPES and amount_paise < 0:
        raise InvalidAdjustmentAmount(adj_type)


# ── Color assignment ──────────────────────────────────────────────────────────

def pick_available_color(used_colors: set[str]) -> str:
    """
    Selects a color from the 12-color palette that is not in `used_colors`.

    Per DB amendment API-2: only colors held by *active* participants
    (left_at IS NULL) count as in-use.  The caller passes only active colors.

    If all 12 colors are in use (possible when room has > 12 active participants),
    returns the first palette color (wrap-around — duplicates are acceptable per PDD §Q11).

    Args:
        used_colors: Set of hex color strings currently in use by active participants.

    Returns:
        A hex color string from COLOR_PALETTE.
    """
    for color in COLOR_PALETTE:
        if color not in used_colors:
            return color
    # All 12 palette colors are in use — wrap to first (duplicate is acceptable).
    return COLOR_PALETTE[0]
