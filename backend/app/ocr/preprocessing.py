from __future__ import annotations

from app.ocr.contracts import PreprocessedImage
from app.ocr.validation import ReceiptImageValidator


class NoOpPreprocessor:
    async def preprocess(self, image: bytes, content_type: str) -> PreprocessedImage:
        validator = ReceiptImageValidator()
        validated = validator.validate(image, content_type)
        return PreprocessedImage(
            content=image,
            content_type=validated.content_type,
            width=validated.width,
            height=validated.height,
            metadata={"preprocessor": "noop"},
        )


class BasicReceiptPreprocessor:
    """Dependency-free normalizer that strips metadata and preserves image pixels."""

    def __init__(self, validator: ReceiptImageValidator | None = None) -> None:
        self._validator = validator or ReceiptImageValidator()

    async def preprocess(self, image: bytes, content_type: str) -> PreprocessedImage:
        validated = self._validator.validate(image, content_type)
        normalized = self._validator.strip_metadata(image, validated.content_type)
        normalized_validation = self._validator.validate(normalized, validated.content_type)
        return PreprocessedImage(
            content=normalized,
            content_type=normalized_validation.content_type,
            width=normalized_validation.width,
            height=normalized_validation.height,
            metadata={"preprocessor": "basic", "metadata_stripped": True},
        )
