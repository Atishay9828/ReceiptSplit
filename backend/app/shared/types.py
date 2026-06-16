"""
ReceiptSplit — Value Objects

Immutable domain primitives used throughout the application.
All money is represented as `Paise` (integer, 1 INR = 100 paise).
No floats anywhere in the money path.

These are not ORM models.  They are pure Python dataclasses used in
the domain and service layers.  ORM columns store their `.value`
attribute directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# ── Constants ──────────────────────────────────────────────────────────────────

#: Regex for UPI VPA validation.  Per PDD §6 / §14.
_VPA_PATTERN: re.Pattern[str] = re.compile(
    r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$"
)

#: 12-color palette assigned to room participants.  Per PDD §Q11.
#: Colors chosen to be visually distinct and accessible.
COLOR_PALETTE: tuple[str, ...] = (
    "#4F46E5",  # Indigo
    "#DB2777",  # Pink
    "#D97706",  # Amber
    "#059669",  # Emerald
    "#DC2626",  # Red
    "#7C3AED",  # Violet
    "#0891B2",  # Cyan
    "#65A30D",  # Lime
    "#EA580C",  # Orange
    "#2563EB",  # Blue
    "#C026D3",  # Fuchsia
    "#0D9488",  # Teal
)

#: Maximum paise value per item (₹1,00,000).  Per PDD §14.
MAX_ITEM_PAISE: int = 10_000_000

#: Maximum paise value per room (₹10,00,000).  Per PDD §14.
MAX_ROOM_PAISE: int = 100_000_000


# ── Paise ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Paise:
    """
    Immutable money value in Indian paise (1 INR = 100 paise).

    Rules:
      - Always non-negative.
      - All arithmetic returns a new Paise instance.
      - No float conversions; use `to_rupees_decimal()` for display only.
    """

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise TypeError(f"Paise value must be int, got {type(self.value).__name__}")
        if self.value < 0:
            raise ValueError(f"Paise value must be >= 0, got {self.value}")

    def __add__(self, other: Paise) -> Paise:
        return Paise(self.value + other.value)

    def __sub__(self, other: Paise) -> Paise:
        result = self.value - other.value
        if result < 0:
            raise ValueError(
                f"Paise subtraction result is negative: {self.value} - {other.value}"
            )
        return Paise(result)

    def __lt__(self, other: Paise) -> bool:
        return self.value < other.value

    def __le__(self, other: Paise) -> bool:
        return self.value <= other.value

    def __gt__(self, other: Paise) -> bool:
        return self.value > other.value

    def __ge__(self, other: Paise) -> bool:
        return self.value >= other.value

    def to_rupees_decimal(self) -> Decimal:
        """
        Converts to a Decimal with exactly 2 decimal places.
        Used only for display and UPI intent generation.
        """
        return (Decimal(self.value) / Decimal(100)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def to_rupees_str(self) -> str:
        """Returns formatted display string, e.g. '₹247.00'."""
        rupees = self.to_rupees_decimal()
        # Indian number formatting: lakh/crore grouping.
        return f"₹{_format_indian(rupees)}"

    def to_upi_amount(self) -> str:
        """
        Returns UPI-spec amount string, e.g. '247.00'.
        Used in upi://pay?am=... URI construction.
        """
        return str(self.to_rupees_decimal())

    @classmethod
    def zero(cls) -> Paise:
        return cls(0)

    def __repr__(self) -> str:
        return f"Paise({self.value})"


def _format_indian(amount: Decimal) -> str:
    """
    Formats a Decimal as Indian number notation.
    e.g. Decimal('100000.00') → '1,00,000.00'
    """
    integer_part, _, decimal_part = str(amount).partition(".")
    # Rightmost 3 digits, then groups of 2.
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last_three = integer_part[-3:]
        rest = integer_part[:-3]
        groups = [rest[max(0, i - 2) : i] for i in range(len(rest), 0, -2)][::-1]
        formatted = ",".join(filter(None, groups)) + "," + last_three
    return f"{formatted}.{decimal_part}"


# ── VPA ───────────────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class VPA:
    """
    UPI Virtual Payment Address.

    Validated against the regex: ^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$
    Max 50 characters.  Per PDD §6 / §14.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError(f"VPA value must be str, got {type(self.value).__name__}")
        if len(self.value) > 50:
            raise ValueError(f"VPA too long (max 50 chars): {self.value!r}")
        if not _VPA_PATTERN.match(self.value):
            raise ValueError(f"Invalid VPA format: {self.value!r}")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"VPA({self.value!r})"


# ── Nickname ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Nickname:
    """
    Participant display name.

    Rules (per PDD §2.3):
      - 1-30 characters
      - Leading/trailing whitespace trimmed before validation
      - HTML tags stripped
      - Null bytes rejected
    """

    value: str

    def __post_init__(self) -> None:
        # Trimming and sanitization are the caller's responsibility
        # (applied in validators.py before construction).
        # Here we only assert the post-sanitization invariants.
        if not isinstance(self.value, str):
            raise TypeError(f"Nickname value must be str, got {type(self.value).__name__}")
        if len(self.value) < 1 or len(self.value) > 30:
            raise ValueError(
                f"Nickname must be 1-30 chars, got {len(self.value)}: {self.value!r}"
            )
        if "\x00" in self.value:
            raise ValueError("Nickname must not contain null bytes")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Nickname({self.value!r})"


# ── Color ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Color:
    """
    Hex color string from the predefined 12-color palette.
    Format: '#RRGGBB' (7 characters).
    """

    hex: str

    def __post_init__(self) -> None:
        if not isinstance(self.hex, str):
            raise TypeError(f"Color hex must be str, got {type(self.hex).__name__}")
        if self.hex not in COLOR_PALETTE:
            raise ValueError(
                f"Color {self.hex!r} is not in the predefined palette"
            )

    def __str__(self) -> str:
        return self.hex

    def __repr__(self) -> str:
        return f"Color({self.hex!r})"
