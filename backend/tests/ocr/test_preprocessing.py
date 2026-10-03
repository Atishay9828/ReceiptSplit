from __future__ import annotations

import io

import pytest
from PIL import Image

from app.ocr.errors import InvalidReceiptImage
from app.ocr.preprocessing import BasicReceiptPreprocessor


def image_bytes(image: Image.Image, format_name: str, **save_options: object) -> bytes:
    output = io.BytesIO()
    image.save(output, format=format_name, **save_options)
    return output.getvalue()


async def test_preprocessor_applies_exif_orientation_before_stripping_metadata() -> None:
    image = Image.new("RGB", (2, 1), "red")
    exif = Image.Exif()
    exif[274] = 6

    result = await BasicReceiptPreprocessor().preprocess(
        image_bytes(image, "JPEG", exif=exif), "image/jpeg"
    )

    with Image.open(io.BytesIO(result.content)) as normalized:
        assert normalized.size == (2, 4)
        assert normalized.getexif().get(274, 1) == 1
    assert result.metadata["orientation_corrected"] is True
    assert result.content_type == "image/png"


async def test_preprocessor_flattens_transparent_png_on_white() -> None:
    image = Image.new("RGBA", (2, 1), (10, 20, 30, 0))
    result = await BasicReceiptPreprocessor().preprocess(
        image_bytes(image, "PNG"), "image/png"
    )

    with Image.open(io.BytesIO(result.content)) as normalized:
        assert normalized.mode == "L"
        assert normalized.getpixel((0, 0)) == 255
    assert result.metadata["alpha_flattened"] is True


async def test_preprocessor_crops_dark_border_scales_and_binarizes() -> None:
    image = Image.new("RGB", (100, 200), "black")
    for x in range(10, 90):
        for y in range(10, 190):
            image.putpixel((x, y), (255, 255, 255))
    image.putpixel((30, 40), (0, 0, 0))

    result = await BasicReceiptPreprocessor().preprocess(
        image_bytes(image, "PNG"), "image/png"
    )

    with Image.open(io.BytesIO(result.content)) as normalized:
        assert normalized.size == (172, 384)
        assert sum(normalized.histogram()[1:255]) == 0
    assert result.metadata["page_cropped"] is True
    assert result.metadata["scale"] == 2.0


async def test_preprocessor_bounds_upscale_for_maximum_input_dimensions() -> None:
    image = Image.new("RGB", (5000, 1), "white")

    result = await BasicReceiptPreprocessor().preprocess(
        image_bytes(image, "PNG"), "image/png"
    )

    assert result.width <= 4000
    assert result.height <= 4000
    assert result.metadata["scale"] < 1.0


async def test_preprocessor_rejects_header_valid_but_undecodable_image() -> None:
    image = image_bytes(Image.new("RGB", (1, 1), "white"), "PNG")[:33]

    with pytest.raises(InvalidReceiptImage, match="corrupt"):
        await BasicReceiptPreprocessor().preprocess(image, "image/png")
