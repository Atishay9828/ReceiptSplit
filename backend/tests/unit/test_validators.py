"""
Tests for app.shared.validators — Input sanitization and validation.

All tests are unit tests (no DB, no I/O).
"""

from __future__ import annotations

import pytest

from app.shared.errors import (
    InvalidAdjustmentAmount,
    InvalidItemName,
    InvalidNickname,
    InvalidVPAFormat,
)
from app.shared.types import COLOR_PALETTE
from app.shared.validators import (
    pick_available_color,
    strip_html,
    validate_adjustment_amount,
    validate_item_name,
    validate_nickname,
    validate_paise,
    validate_vpa,
)


# ── strip_html ─────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestStripHtml:
    def test_plain_text_unchanged(self):
        assert strip_html("Priya") == "Priya"

    def test_removes_script_tag(self):
        result = strip_html("<script>alert('xss')</script>Priya")
        assert "<script>" not in result
        assert "Priya" in result

    def test_removes_html_entities_tags(self):
        result = strip_html("<b>bold</b>")
        assert "<b>" not in result
        assert "bold" in result

    def test_removes_null_bytes(self):
        assert "\x00" not in strip_html("hello\x00world")

    def test_strips_leading_trailing_whitespace(self):
        assert strip_html("  Priya  ") == "Priya"

    def test_empty_string_stays_empty(self):
        assert strip_html("") == ""


# ── validate_nickname ─────────────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateNickname:
    def test_valid(self):
        n = validate_nickname("Priya")
        assert n.value == "Priya"

    def test_strips_html(self):
        n = validate_nickname("<b>Priya</b>")
        assert n.value == "Priya"

    def test_trims_whitespace(self):
        n = validate_nickname("  Priya  ")
        assert n.value == "Priya"

    def test_empty_after_strip_raises(self):
        with pytest.raises(InvalidNickname):
            validate_nickname("<script></script>")

    def test_too_long_raises(self):
        with pytest.raises(InvalidNickname):
            validate_nickname("A" * 31)

    def test_exactly_30_chars_valid(self):
        n = validate_nickname("A" * 30)
        assert len(n.value) == 30


# ── validate_item_name ────────────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateItemName:
    def test_valid(self):
        assert validate_item_name("Butter Chicken") == "Butter Chicken"

    def test_strips_html(self):
        assert validate_item_name("<em>Naan</em>") == "Naan"

    def test_empty_raises(self):
        with pytest.raises(InvalidItemName):
            validate_item_name("")

    def test_201_chars_raises(self):
        with pytest.raises(InvalidItemName):
            validate_item_name("A" * 201)

    def test_200_chars_valid(self):
        result = validate_item_name("A" * 200)
        assert len(result) == 200


# ── validate_vpa ──────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateVpa:
    def test_valid(self):
        v = validate_vpa("user@upi")
        assert v.value == "user@upi"

    def test_strips_whitespace(self):
        v = validate_vpa("  user@upi  ")
        assert v.value == "user@upi"

    def test_invalid_raises(self):
        with pytest.raises(InvalidVPAFormat):
            validate_vpa("notavpa")

    def test_too_long_raises(self):
        with pytest.raises(InvalidVPAFormat):
            validate_vpa("a" * 50 + "@b")


# ── validate_paise ────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestValidatePaise:
    def test_valid_zero(self):
        p = validate_paise(0, max_value=10_000_000)
        assert p.value == 0

    def test_valid_max(self):
        p = validate_paise(10_000_000, max_value=10_000_000)
        assert p.value == 10_000_000

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            validate_paise(-1, max_value=10_000_000)

    def test_exceeds_max_raises(self):
        with pytest.raises(ValueError):
            validate_paise(10_000_001, max_value=10_000_000)

    def test_float_raises(self):
        with pytest.raises(ValueError):
            validate_paise(100.5, max_value=10_000_000)  # type: ignore[arg-type]


# ── validate_adjustment_amount ────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateAdjustmentAmount:
    @pytest.mark.parametrize("adj_type", ["tax", "service_charge", "delivery_fee", "discount"])
    def test_positive_always_valid(self, adj_type: str):
        # Should not raise
        validate_adjustment_amount(adj_type, 1000)

    @pytest.mark.parametrize("adj_type", ["tax", "service_charge", "delivery_fee", "discount"])
    def test_negative_raises_for_non_adjustment_types(self, adj_type: str):
        with pytest.raises(InvalidAdjustmentAmount):
            validate_adjustment_amount(adj_type, -1)

    def test_negative_adjustment_type_is_valid(self):
        # Amendment DB-4: 'adjustment' type may be negative for OCR reconciliation
        validate_adjustment_amount("adjustment", -500)   # must not raise

    def test_zero_is_valid_for_all_types(self):
        for adj_type in ["tax", "service_charge", "delivery_fee", "discount", "adjustment"]:
            validate_adjustment_amount(adj_type, 0)  # must not raise


# ── pick_available_color ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestPickAvailableColor:
    def test_picks_first_available(self):
        color = pick_available_color(set())
        assert color in COLOR_PALETTE

    def test_skips_used_colors(self):
        used = set(COLOR_PALETTE[:11])   # use 11 of 12
        color = pick_available_color(used)
        assert color == COLOR_PALETTE[11]

    def test_left_participant_color_is_available(self):
        """
        Amendment API-2: colors held by left participants must be reusable.
        Caller passes only ACTIVE participant colors to this function.
        """
        # Simulate: one active participant uses COLOR_PALETTE[0].
        # Left participants' colors are NOT in used_colors — caller filters them.
        active_colors = {COLOR_PALETTE[0]}
        color = pick_available_color(active_colors)
        assert color != COLOR_PALETTE[0]

    def test_wraps_when_all_used(self):
        """When all 12 colors are in use (>12 active participants), wraps to first."""
        all_colors = set(COLOR_PALETTE)
        color = pick_available_color(all_colors)
        assert color == COLOR_PALETTE[0]
