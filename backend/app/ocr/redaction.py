from __future__ import annotations

import re

CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
UPI_RE = re.compile(r"\b[a-zA-Z0-9._-]{2,}@[a-zA-Z][a-zA-Z0-9._-]{2,}\b")


def redact_sensitive_ocr_text(text: str) -> str:
    redacted = CARD_RE.sub("[redacted-card]", text)
    redacted = PHONE_RE.sub("[redacted-phone]", redacted)
    redacted = EMAIL_RE.sub("[redacted-email]", redacted)
    return UPI_RE.sub("[redacted-upi]", redacted)
