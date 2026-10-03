from __future__ import annotations

import asyncio
import io

from PIL import Image, ImageOps

from app.ocr.contracts import PreprocessedImage
from app.ocr.validation import ReceiptImageValidator

MAX_OCR_IMAGE_SIDE = 4000
UPSCALE_FACTOR = 2.0
PAGE_EDGE_THRESHOLD = 210
BINARIZATION_THRESHOLD = 190


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
    """Bounded EXIF, page-boundary, contrast, scale, and binarization pipeline."""

    def __init__(self, validator: ReceiptImageValidator | None = None) -> None:
        self._validator = validator or ReceiptImageValidator()

    async def preprocess(self, image: bytes, content_type: str) -> PreprocessedImage:
        return await asyncio.to_thread(self._preprocess_sync, image, content_type)

    def _preprocess_sync(self, image: bytes, content_type: str) -> PreprocessedImage:
        self._validator.validate(image, content_type)
        try:
            with Image.open(io.BytesIO(image)) as source:
                source.load()
                orientation = source.getexif().get(274, 1)
                has_alpha = source.mode in {"RGBA", "LA"} or "transparency" in source.info
                normalized_image = ImageOps.exif_transpose(source)
                if has_alpha:
                    rgba = normalized_image.convert("RGBA")
                    flattened = Image.new("RGB", rgba.size, (255, 255, 255))
                    flattened.paste(rgba, mask=rgba.getchannel("A"))
                    normalized_image = flattened

                grayscale = ImageOps.grayscale(normalized_image)
                grayscale, page_cropped = _crop_receipt_from_dark_background(grayscale)
                scale = min(
                    UPSCALE_FACTOR,
                    MAX_OCR_IMAGE_SIDE / grayscale.width,
                    MAX_OCR_IMAGE_SIDE / grayscale.height,
                )
                if scale != 1.0:
                    grayscale = grayscale.resize(
                        (round(grayscale.width * scale), round(grayscale.height * scale)),
                        Image.Resampling.LANCZOS,
                    )

                enhanced = ImageOps.autocontrast(grayscale, cutoff=1)
                normalized_image = enhanced.point(
                    lambda pixel: 255 if pixel > BINARIZATION_THRESHOLD else 0
                )
                output = io.BytesIO()
                normalized_image.save(output, format="PNG", optimize=True)
                normalized = output.getvalue()
        except (Image.DecompressionBombError, OSError, ValueError):
            from app.ocr.errors import InvalidReceiptImage

            raise InvalidReceiptImage("corrupt image") from None

        normalized_validation = self._validator.validate(normalized, "image/png")
        return PreprocessedImage(
            content=normalized,
            content_type=normalized_validation.content_type,
            width=normalized_validation.width,
            height=normalized_validation.height,
            metadata={
                "preprocessor": "receipt-binarize-v1",
                "metadata_stripped": True,
                "orientation_corrected": orientation != 1,
                "alpha_flattened": has_alpha,
                "page_cropped": page_cropped,
                "scale": round(scale, 3),
                "threshold": BINARIZATION_THRESHOLD,
            },
        )


def _crop_receipt_from_dark_background(image: Image.Image) -> tuple[Image.Image, bool]:
    """Trim a clearly bounded light page while retaining a small safety margin."""
    bright_pixels = image.point(lambda pixel: 255 if pixel >= PAGE_EDGE_THRESHOLD else 0)
    bounds = bright_pixels.getbbox()
    if bounds is None:
        return image, False

    left, top, right, bottom = bounds
    cropped_area = (right - left) * (bottom - top)
    image_area = image.width * image.height
    has_dark_margin = (
        left >= image.width * 0.01
        and top >= image.height * 0.01
        and image.width - right >= image.width * 0.01
    )
    if cropped_area >= image_area * 0.93 or not has_dark_margin:
        return image, False

    horizontal_padding = round(image.width * 0.03)
    vertical_padding = round(image.height * 0.03)
    crop = (
        max(0, left - horizontal_padding),
        max(0, top - vertical_padding),
        min(image.width, right + horizontal_padding),
        min(image.height, bottom + vertical_padding),
    )
    return image.crop(crop), True
