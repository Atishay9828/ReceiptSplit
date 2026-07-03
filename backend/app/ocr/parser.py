from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.ocr.contracts import (
    ParsedReceiptAdjustment,
    ParsedReceiptDraft,
    ParsedReceiptLine,
)

MONEY_RE = re.compile(r"(?<!\d)-?\d+(?:,\d{3})*(?:\.\d{1,2})?(?!\d)")
QTY_PRICE_RE = re.compile(
    r"^(?P<name>.+?)\s+(?P<qty>\d{1,3})\s*[xX]\s*(?P<unit>\d+(?:\.\d{1,2})?)\s+(?P<total>\d+(?:\.\d{1,2})?)$"
)
NOISE_PATTERNS = (
    "thank you",
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
)


class IndianRestaurantReceiptParser:
    parser_version = "indian_restaurant_v1"

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
        rounding_paise = 0
        total_paise: int | None = None

        for index, line in enumerate(lines):
            lower = line.lower()
            if index == 0 or self._is_noise(lower):
                continue

            amount = self._last_money(line)
            if amount is None:
                if self._looks_like_item(line):
                    warnings.append("ambiguous_line")
                continue

            amount_paise = self._money_to_paise(amount)
            if self._is_subtotal(lower):
                subtotal_paise = amount_paise
                continue
            if self._is_total(lower):
                total_paise = amount_paise
                continue
            if self._is_tax_or_charge(lower):
                tax_paise = (tax_paise or 0) + amount_paise
                adjustments.append(
                    ParsedReceiptAdjustment(
                        type="service_charge" if "service" in lower else "tax",
                        label=self._label_without_money(line),
                        amount_paise=amount_paise,
                    )
                )
                self._append_once(warnings, "tax_detected")
                continue
            if "discount" in lower:
                discount_paise = -abs(amount_paise)
                adjustments.append(
                    ParsedReceiptAdjustment(
                        type="discount",
                        label=self._label_without_money(line),
                        amount_paise=discount_paise,
                    )
                )
                self._append_once(warnings, "discount_detected")
                continue
            if "round" in lower:
                rounding_paise = amount_paise if "-" not in amount else amount_paise * -1
                continue

            item = self._parse_item_line(line)
            if item is None:
                self._append_once(warnings, "low_confidence_line")
            else:
                items.append(item)

        item_total = sum(item.total_paise for item in items)
        calculated_total = item_total + (tax_paise or 0) + (discount_paise or 0) + rounding_paise
        if total_paise is not None and items and abs(calculated_total - total_paise) > 100:
            self._append_once(warnings, "items_sum_mismatch")

        if total_paise is None:
            self._append_once(warnings, "missing_total")

        needs_review = bool(
            set(warnings)
            & {"missing_total", "items_sum_mismatch", "low_confidence_line", "ambiguous_line"}
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

    def _parse_item_line(self, line: str) -> ParsedReceiptLine | None:
        match = QTY_PRICE_RE.match(line)
        if match:
            name = self._clean_name(match.group("name"))
            return ParsedReceiptLine(
                name=name,
                quantity=int(match.group("qty")),
                unit_price_paise=self._money_to_paise(match.group("unit")),
                total_paise=self._money_to_paise(match.group("total")),
            )

        amount = self._last_money(line)
        if amount is None:
            return None
        name = self._clean_name(line[: line.rfind(amount)])
        if not name:
            return None
        return ParsedReceiptLine(
            name=name,
            quantity=1,
            unit_price_paise=None,
            total_paise=self._money_to_paise(amount),
        )

    def _parse_money(self, value: str) -> Decimal:
        try:
            return Decimal(value.replace(",", ""))
        except InvalidOperation:
            return Decimal("0")

    def _money_to_paise(self, value: str) -> int:
        return int((self._parse_money(value).copy_abs() * Decimal("100")).quantize(Decimal("1")))

    def _last_money(self, line: str) -> str | None:
        matches = MONEY_RE.findall(line)
        return matches[-1] if matches else None

    def _label_without_money(self, line: str) -> str:
        amount = self._last_money(line)
        return self._clean_name(line.replace(amount, "")) if amount else self._clean_name(line)

    def _normalize_line(self, line: str) -> str:
        return re.sub(r"\s+", " ", line.strip())

    def _merchant_name(self, lines: list[str]) -> str | None:
        if not lines:
            return None
        return self._clean_name(lines[0]).upper()

    def _clean_name(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9 &().,'/-]+", " ", value)
        return re.sub(r"\s+", " ", cleaned).strip(" -")

    def _is_noise(self, lower: str) -> bool:
        return any(pattern in lower for pattern in NOISE_PATTERNS)

    def _is_subtotal(self, lower: str) -> bool:
        return "subtotal" in lower or "sub total" in lower

    def _is_total(self, lower: str) -> bool:
        return "total" in lower and not self._is_subtotal(lower)

    def _is_tax_or_charge(self, lower: str) -> bool:
        return any(token in lower for token in ("cgst", "sgst", "igst", "tax", "service charge"))

    def _looks_like_item(self, line: str) -> bool:
        return bool(re.search(r"[A-Za-z]", line))

    def _append_once(self, warnings: list[str], warning: str) -> None:
        if warning not in warnings:
            warnings.append(warning)
