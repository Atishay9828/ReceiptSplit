from __future__ import annotations

from app.ocr.redaction import redact_sensitive_ocr_text


def test_redacts_sensitive_receipt_text() -> None:
    text = "Card 4111 1111 1111 1111 phone 9876543210 email aj@example.com upi aj@okaxis"

    redacted = redact_sensitive_ocr_text(text)

    assert "4111" not in redacted
    assert "9876543210" not in redacted
    assert "aj@example.com" not in redacted
    assert "aj@okaxis" not in redacted
