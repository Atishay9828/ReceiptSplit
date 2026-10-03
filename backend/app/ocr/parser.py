from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

from app.ocr.contracts import (
    ParsedReceiptAdjustment,
    ParsedReceiptDraft,
    ParsedReceiptLine,
)
from app.shared.types import MAX_ITEM_PAISE, MAX_ROOM_PAISE

MONEY_RE = re.compile(r"(?<!\d)-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:[.,]\d{1,2})?(?!\d)")
MONEY_VALUE = r"\d+(?:[.,]\d{1,2})?"
CURRENCY_PREFIX = r"(?:₹|Rs\.?|INR)?\s*"
QTY_PRICE_RE = re.compile(
    rf"^(?P<name>.+?)\s+(?P<qty>\d{{1,3}})\s*[xX]\s*{CURRENCY_PREFIX}"
    rf"(?P<unit>{MONEY_VALUE})\s+{CURRENCY_PREFIX}(?P<total>{MONEY_VALUE})$"
)
QTY_X_TOTAL_RE = re.compile(
    rf"^(?P<name>.+?)\s+[xX]\s*(?P<qty>\d{{1,3}})\s*{CURRENCY_PREFIX}"
    rf"(?P<total>{MONEY_VALUE})$"
)
QTY_TIMES_TOTAL_RE = re.compile(
    rf"^(?P<name>.+?)\s+(?P<qty>\d{{1,3}})\s*[xX]\s*{CURRENCY_PREFIX}"
    rf"(?P<total>{MONEY_VALUE})$"
)
LEADING_QTY_COLUMN_RE = re.compile(
    rf"^(?P<qty>\d{{1,3}})\s+(?P<name>.+?)\s+{CURRENCY_PREFIX}"
    rf"(?P<unit>{MONEY_VALUE})\s+{CURRENCY_PREFIX}(?P<total>{MONEY_VALUE})$"
)
LEADING_QTY_RE = re.compile(
    rf"^(?P<qty>\d{{1,3}})\s+(?P<name>.+?)\s+{CURRENCY_PREFIX}(?P<total>{MONEY_VALUE})$"
)
NOISE_PATTERNS = (
    "thank you",
    "hope to see you",
    "visit again",
    "gstin",
    "fssai",
    "phone",
    "address",
    "invoice",
    "date",
    "time",
    "cashier",
    "payment mode",
    "card",
    "upi ref",
    "paid in full",
    "server",
    "order #",
    "order no",
    "table",
)


class IndianRestaurantReceiptParser:
    parser_version = "indian_restaurant_v3"

    def parse(self, raw_text: str) -> ParsedReceiptDraft:
        lines = [self._normalize_line(line) for line in raw_text.splitlines()]
        lines = [line for line in lines if line]
        merchant_name = self._merchant_name(lines)
        items: list[ParsedReceiptLine] = []
        adjustments: list[ParsedReceiptAdjustment] = []
        warnings: list[str] = []
        subtotal_paise: int | None = None
        tax_paise: int | None = None
        discount_paise: int | None = None
        named_tax_paise = 0
        aggregate_tax_paise: int | None = None
        total_paise: int | None = None
        pending_item_name: str | None = None

        for index, line in enumerate(lines):
            lower = line.lower()
            if index == 0 or self._is_noise(lower):
                continue

            if self._is_tax_or_charge(lower) and re.search(r"(?<!\w)r\d+\b", line, re.IGNORECASE):
                self._append_once(warnings, "unresolved_adjustment_amount")
                continue

            amount = self._last_money(line)
            if amount is None:
                if self._is_tax_or_charge(lower) and "%" in lower:
                    self._append_once(warnings, "unresolved_adjustment_amount")
                elif self._looks_like_item(line):
                    pending_item_name = (
                        f"{pending_item_name} {line}" if pending_item_name else line
                    )
                continue

            if pending_item_name and not (
                self._is_subtotal(lower)
                or self._is_total(lower)
                or self._is_tax_or_charge(lower)
                or any(token in lower for token in ("discount", "coupon", "offer", "round"))
            ):
                line = f"{pending_item_name} {line}"
                lower = line.lower()
                pending_item_name = None

            amount_paise = self._money_to_paise(amount)
            if self._is_subtotal(lower):
                if amount_paise > MAX_ROOM_PAISE:
                    self._append_once(warnings, "invalid_total_amount")
                    continue
                subtotal_paise = amount_paise
                continue
            if self._is_tax_summary(lower):
                if amount_paise > 10_000_000:
                    self._append_once(warnings, "unresolved_adjustment_amount")
                elif self._is_tax_or_charge(lower):
                    aggregate_tax_paise = amount_paise
                continue
            if self._is_tax_or_charge(lower):
                is_service_charge = any(
                    token in lower for token in ("service", "delivery", "packaging")
                )
                if amount_paise <= 0 or amount_paise > 10_000_000:
                    self._append_once(warnings, "unresolved_adjustment_amount")
                    continue
                is_component_tax = any(token in lower for token in ("cgst", "sgst", "igst"))
                if not is_service_charge and not is_component_tax and named_tax_paise:
                    aggregate_tax_paise = amount_paise
                    continue
                if not is_service_charge:
                    named_tax_paise += amount_paise
                adjustments.append(
                    ParsedReceiptAdjustment(
                        type=self._adjustment_type(lower),
                        label=self._label_without_money(line),
                        amount_paise=amount_paise,
                    )
                )
                self._append_once(
                    warnings,
                    "service_charge_detected" if is_service_charge else "tax_detected",
                )
                continue
            if self._is_total(lower):
                if amount_paise > MAX_ROOM_PAISE:
                    self._append_once(warnings, "invalid_total_amount")
                    continue
                total_paise = amount_paise
                continue
            if "discount" in lower or "coupon" in lower or "offer" in lower:
                if amount_paise > 10_000_000:
                    self._append_once(warnings, "unresolved_adjustment_amount")
                    continue
                discount_paise = -abs(amount_paise)
                adjustments.append(
                    ParsedReceiptAdjustment(
                        type="coupon"
                        if "coupon" in lower
                        else "offer"
                        if "offer" in lower
                        else "discount",
                        label=self._label_without_money(line),
                        amount_paise=discount_paise,
                    )
                )
                self._append_once(warnings, "discount_detected")
                continue
            if "round" in lower:
                if amount_paise > 10_000_000:
                    self._append_once(warnings, "unresolved_adjustment_amount")
                    continue
                signed_amount_paise = amount_paise if "-" not in amount else -amount_paise
                adjustments.append(
                    ParsedReceiptAdjustment(
                        type="rounding",
                        label=self._label_without_money(line) or "Rounding",
                        amount_paise=signed_amount_paise,
                    )
                )
                continue

            item = self._parse_item_line(line, warnings)
            if item is None:
                self._append_once(warnings, "low_confidence_line")
            else:
                items.append(item)

        if pending_item_name:
            self._append_once(warnings, "ambiguous_line")

        tax_paise = named_tax_paise or None
        if aggregate_tax_paise is not None:
            if named_tax_paise and aggregate_tax_paise != named_tax_paise:
                self._append_once(warnings, "tax_summary_mismatch")
            elif not named_tax_paise:
                tax_paise = aggregate_tax_paise
                adjustments.append(
                    ParsedReceiptAdjustment(
                        type="tax", label="Tax", amount_paise=aggregate_tax_paise
                    )
                )
        item_total = sum(item.total_paise for item in items)
        if subtotal_paise is not None and items and subtotal_paise != item_total:
            self._append_once(warnings, "items_subtotal_mismatch")
        calculated_total = item_total + sum(adjustment.amount_paise for adjustment in adjustments)
        if total_paise is not None and items and calculated_total != total_paise:
            self._append_once(warnings, "items_sum_mismatch")

        if total_paise is None:
            self._append_once(warnings, "missing_total")

        needs_review = bool(
            set(warnings)
            & {
                "missing_total",
                "items_sum_mismatch",
                "low_confidence_line",
                "ambiguous_line",
                "quantity_total_inferred",
                "items_subtotal_mismatch",
                "tax_summary_mismatch",
                "unresolved_adjustment_amount",
                "quantity_price_mismatch",
                "invalid_item_amount",
                "invalid_total_amount",
            }
        )
        if not items:
            needs_review = True

        confidence = 0.95 if not needs_review else 0.55
        return ParsedReceiptDraft(
            merchant_name=merchant_name,
            subtotal_paise=subtotal_paise,
            tax_paise=tax_paise,
            discount_paise=discount_paise,
            total_paise=total_paise,
            items=items,
            adjustments=adjustments,
            warnings=warnings,
            confidence=confidence,
            needs_review=needs_review,
            parser_version=self.parser_version,
        )

    def _parse_item_line(self, line: str, warnings: list[str]) -> ParsedReceiptLine | None:
        line = re.sub(r"^[^A-Za-z0-9]+(?=\d{1,3}\s+[A-Za-z])", "", line)
        leading_columns = LEADING_QTY_COLUMN_RE.match(line)
        if leading_columns:
            quantity = int(leading_columns.group("qty"))
            unit_paise = self._money_to_paise(leading_columns.group("unit"))
            total_paise = self._money_to_paise(leading_columns.group("total"))
            if unit_paise > MAX_ITEM_PAISE or total_paise > MAX_ITEM_PAISE:
                self._append_once(warnings, "invalid_item_amount")
                return None
            if unit_paise * quantity != total_paise:
                self._append_once(warnings, "quantity_price_mismatch")
            return ParsedReceiptLine(
                name=self._clean_name(leading_columns.group("name")),
                quantity=quantity,
                unit_price_paise=unit_paise,
                total_paise=total_paise,
            )

        match = QTY_PRICE_RE.match(line)
        if match:
            name = self._clean_name(match.group("name"))
            return ParsedReceiptLine(
                name=name,
                quantity=int(match.group("qty")),
                unit_price_paise=self._money_to_paise(match.group("unit")),
                total_paise=self._money_to_paise(match.group("total")),
            )

        for quantity_total_pattern in (QTY_X_TOTAL_RE, QTY_TIMES_TOTAL_RE):
            match = quantity_total_pattern.match(line)
            if match:
                quantity = int(match.group("qty"))
                total_paise = self._money_to_paise(match.group("total"))
                self._append_once(warnings, "quantity_total_inferred")
                return ParsedReceiptLine(
                    name=self._clean_name(match.group("name")),
                    quantity=quantity,
                    unit_price_paise=(total_paise // quantity)
                    if total_paise % quantity == 0
                    else None,
                    total_paise=total_paise,
                )

        leading_quantity = LEADING_QTY_RE.match(line)
        if leading_quantity:
            quantity = int(leading_quantity.group("qty"))
            total_paise = self._money_to_paise(leading_quantity.group("total"))
            if quantity > 1:
                self._append_once(warnings, "quantity_total_inferred")
            return ParsedReceiptLine(
                name=self._clean_name(leading_quantity.group("name")),
                quantity=quantity,
                unit_price_paise=(total_paise // quantity)
                if quantity > 0 and total_paise % quantity == 0
                else None,
                total_paise=total_paise,
            )

        amount = self._last_money(line)
        if amount is None:
            return None
        total_paise = self._money_to_paise(amount)
        if total_paise > MAX_ITEM_PAISE:
            self._append_once(warnings, "invalid_item_amount")
            return None
        name = self._clean_name(line[: line.rfind(amount)])
        if not name:
            return None
        return ParsedReceiptLine(
            name=name,
            quantity=1,
            unit_price_paise=None,
            total_paise=total_paise,
        )

    def _parse_money(self, value: str) -> Decimal:
        try:
            normalized = value.replace(",", "") if "." in value else value.replace(",", ".")
            return Decimal(normalized)
        except InvalidOperation:
            return Decimal("0")

    def _money_to_paise(self, value: str) -> int:
        return int((self._parse_money(value).copy_abs() * Decimal("100")).quantize(Decimal("1")))

    def _last_money(self, line: str) -> str | None:
        matches = [
            match.group(0)
            for match in MONEY_RE.finditer(line)
            if not re.match(r"\s*%", line[match.end() :])
        ]
        return matches[-1] if matches else None

    def _label_without_money(self, line: str) -> str:
        amount = self._last_money(line)
        return self._clean_name(line.replace(amount, "")) if amount else self._clean_name(line)

    def _normalize_line(self, line: str) -> str:
        normalized = re.sub(r"\s+", " ", line.strip())
        # Tesseract often substitutes common currency symbols before a numeric token.
        return re.sub(r"(?<!\w)[₹$£%]\s*(?=\d)", "", normalized)

    def _merchant_name(self, lines: list[str]) -> str | None:
        if not lines:
            return None
        return self._clean_name(lines[0]).upper()

    def _clean_name(self, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value)
        cleaned = "".join(
            character
            if character.isalnum() or character in " &().,'/-"
            else " "
            for character in normalized
        )
        return re.sub(r"\s+", " ", cleaned).strip(" -")

    def _is_noise(self, lower: str) -> bool:
        if any(pattern in lower for pattern in NOISE_PATTERNS):
            return True
        if re.search(
            r"^\d+\s+.+\b(?:street|st|road|rd|lane|avenue|ave|drive|dr|way|boulevard|blvd)\b",
            lower,
        ):
            return True
        if re.fullmatch(r"[a-z .'-]+,\s*[a-z]{2}\s+\d{5}(?:-\d{4})?", lower):
            return True
        return sum(character.isdigit() for character in lower) >= 8 and not re.search(
            r"[a-z]{3,}", lower
        )

    def _is_subtotal(self, lower: str) -> bool:
        return "subtotal" in lower or "sub total" in lower

    def _is_total(self, lower: str) -> bool:
        return "total" in lower and not self._is_subtotal(lower)

    def _is_tax_or_charge(self, lower: str) -> bool:
        return bool(
            re.search(r"\b(?:cgst|sgst|igst|gst|tax(?:es)?)\b", lower)
            or any(
                token in lower for token in ("service charge", "delivery fee", "packaging fee")
            )
        )

    def _is_tax_summary(self, lower: str) -> bool:
        return bool(
            re.search(r"\b(?:(?:total|grand|summary)\s+tax(?:es)?|tax(?:es)?\s+total)\b", lower)
        )

    def _adjustment_type(self, lower: str) -> str:
        if "service" in lower:
            return "service_charge"
        if "delivery" in lower:
            return "delivery_fee"
        if "packaging" in lower:
            return "packaging_fee"
        return "tax"

    def _looks_like_item(self, line: str) -> bool:
        return bool(re.search(r"[A-Za-z]", line))

    def _append_once(self, warnings: list[str], warning: str) -> None:
        if warning not in warnings:
            warnings.append(warning)
