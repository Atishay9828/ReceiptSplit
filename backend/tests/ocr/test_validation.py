from __future__ import annotations

import pytest

from app.ocr.errors import InvalidReceiptImage
from app.ocr.validation import ImageValidationConfig, ReceiptImageValidator

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xe2'"
    b"\xb5\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_upload_accepts_valid_png() -> None:
    validator = ReceiptImageValidator(ImageValidationConfig(max_bytes=1024))

    result = validator.validate(PNG_1X1, "image/png")

    assert result.content_type == "image/png"
    assert result.width == 1
    assert result.height == 1


def test_upload_rejects_non_image() -> None:
    validator = ReceiptImageValidator(ImageValidationConfig(max_bytes=1024))

    with pytest.raises(InvalidReceiptImage, match="unsupported image type"):
        validator.validate(b"not an image", "text/plain")


def test_upload_rejects_too_large_image() -> None:
    validator = ReceiptImageValidator(ImageValidationConfig(max_bytes=4))

    with pytest.raises(InvalidReceiptImage, match="too large"):
        validator.validate(PNG_1X1, "image/png")


def test_upload_rejects_corrupt_image() -> None:
    validator = ReceiptImageValidator(ImageValidationConfig(max_bytes=1024))

    with pytest.raises(InvalidReceiptImage, match="corrupt"):
        validator.validate(b"\x89PNG\r\n\x1a\nbroken", "image/png")


def test_upload_strips_exif_png_ancillary_chunks() -> None:
    validator = ReceiptImageValidator(ImageValidationConfig(max_bytes=2048))
    png_with_text_chunk = (
        PNG_1X1[:33]
        + b"\x00\x00\x00\x08tEXtsecret!!\x00\x00\x00\x00"
        + PNG_1X1[33:]
    )

    sanitized = validator.strip_metadata(png_with_text_chunk, "image/png")

    assert b"secret" not in sanitized
    assert sanitized.startswith(b"\x89PNG\r\n\x1a\n")
