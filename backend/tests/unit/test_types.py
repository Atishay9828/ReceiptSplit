"""
Tests for app.shared.types — Value objects.

All tests are unit tests (no DB, no I/O).
Marked with @pytest.mark.unit.
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from app.shared.types import COLOR_PALETTE, Color, Nickname, Paise, VPA


# ── Paise ──────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestPaise:
    def test_zero_is_valid(self):
        p = Paise(0)
        assert p.value == 0

    def test_positive_is_valid(self):
        p = Paise(24700)
        assert p.value == 24700

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            Paise(-1)

    def test_float_raises(self):
        with pytest.raises(TypeError, match="must be int"):
            Paise(247.50)  # type: ignore[arg-type]

    def test_addition(self):
        assert Paise(100) + Paise(200) == Paise(300)

    def test_subtraction_valid(self):
        assert Paise(300) - Paise(100) == Paise(200)

    def test_subtraction_to_zero(self):
        assert Paise(100) - Paise(100) == Paise(0)

    def test_subtraction_negative_raises(self):
        with pytest.raises(ValueError, match="negative"):
            Paise(100) - Paise(200)

    def test_comparison(self):
        assert Paise(100) < Paise(200)
        assert Paise(200) > Paise(100)
        assert Paise(100) <= Paise(100)
        assert Paise(100) >= Paise(100)

    def test_equality(self):
        assert Paise(100) == Paise(100)
        assert Paise(100) != Paise(200)

    def test_to_rupees_decimal(self):
        assert Paise(24700).to_rupees_decimal() == Decimal("247.00")

    def test_to_rupees_decimal_rounding(self):
        # 1 paise = 0.01 INR exactly
        assert Paise(1).to_rupees_decimal() == Decimal("0.01")

    def test_to_upi_amount(self):
        assert Paise(24700).to_upi_amount() == "247.00"

    def test_to_rupees_str_contains_symbol(self):
        result = Paise(24700).to_rupees_str()
        assert "₹" in result
        assert "247.00" in result

    def test_zero_factory(self):
        assert Paise.zero() == Paise(0)

    def test_immutable(self):
        p = Paise(100)
        with pytest.raises(AttributeError):
            p.value = 200  # type: ignore[misc]

    def test_repr(self):
        assert repr(Paise(100)) == "Paise(100)"


# ── VPA ───────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestVPA:
    @pytest.mark.parametrize("vpa", [
        "user@upi",
        "john.doe@okaxis",
        "mobile123@paytm",
        "name-with-dash@icici",
        "a@b",
    ])
    def test_valid_vpa(self, vpa: str):
        v = VPA(vpa)
        assert v.value == vpa

    @pytest.mark.parametrize("bad", [
        "",
        "notavpa",
        "@nousername",
        "user@",
        "user@@bank",
        "user @bank",
        "a" * 51 + "@b",
    ])
    def test_invalid_vpa_raises(self, bad: str):
        with pytest.raises(ValueError):
            VPA(bad)

    def test_str(self):
        assert str(VPA("user@upi")) == "user@upi"

    def test_immutable(self):
        v = VPA("user@upi")
        with pytest.raises(AttributeError):
            v.value = "other@upi"  # type: ignore[misc]


# ── Nickname ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestNickname:
    def test_valid_single_char(self):
        n = Nickname("A")
        assert n.value == "A"

    def test_valid_30_chars(self):
        n = Nickname("A" * 30)
        assert len(n.value) == 30

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="1–30"):
            Nickname("")

    def test_31_chars_raises(self):
        with pytest.raises(ValueError, match="1–30"):
            Nickname("A" * 31)

    def test_null_byte_raises(self):
        with pytest.raises(ValueError, match="null bytes"):
            Nickname("hello\x00world")

    def test_str(self):
        assert str(Nickname("Priya")) == "Priya"

    def test_immutable(self):
        n = Nickname("Priya")
        with pytest.raises(AttributeError):
            n.value = "Rahul"  # type: ignore[misc]


# ── Color ─────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestColor:
    def test_valid_palette_color(self):
        c = Color(COLOR_PALETTE[0])
        assert c.hex == COLOR_PALETTE[0]

    def test_all_palette_colors_are_valid(self):
        for hex_color in COLOR_PALETTE:
            c = Color(hex_color)
            assert c.hex == hex_color

    def test_invalid_color_raises(self):
        with pytest.raises(ValueError, match="not in the predefined palette"):
            Color("#000000")  # not in our palette

    def test_arbitrary_hex_raises(self):
        with pytest.raises(ValueError):
            Color("#FF0000")

    def test_str(self):
        c = Color(COLOR_PALETTE[0])
        assert str(c) == COLOR_PALETTE[0]

    def test_palette_has_12_colors(self):
        assert len(COLOR_PALETTE) == 12

    def test_palette_all_7_chars(self):
        for color in COLOR_PALETTE:
            assert len(color) == 7
            assert color.startswith("#")
