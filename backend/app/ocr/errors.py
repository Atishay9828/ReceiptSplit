from __future__ import annotations

from app.shared.errors import DomainError


class InvalidReceiptImage(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            code="INVALID_RECEIPT_IMAGE",
            message=f"Receipt image is invalid: {reason}.",
        )


class OcrProviderUnavailable(DomainError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            code="OCR_PROVIDER_UNAVAILABLE",
            message=f"{provider} OCR is unavailable on this server.",
        )


class OcrProviderTimeout(DomainError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            code="OCR_PROVIDER_TIMEOUT",
            message=f"{provider} OCR timed out. Try a clearer image or enter items manually.",
        )


class OcrProviderFailed(DomainError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            code="OCR_PROVIDER_FAILED",
            message=f"{provider} OCR failed. Try a clearer image or enter items manually.",
        )


class ParsedReceiptNotFound(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PARSED_RECEIPT_NOT_FOUND",
            message="Parsed receipt draft not found.",
        )


class OcrJobNotFound(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="OCR_JOB_NOT_FOUND",
            message="OCR job not found.",
        )
