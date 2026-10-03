"""Render authored receipt text into deterministic, high-contrast OCR fixtures."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "receipts"
IMAGE_ROOT = FIXTURE_ROOT / "images"
FIXTURE_NAMES = (
    "sample_restaurant_expected",
    "simple_restaurant",
    "gst_cgst_sgst",
    "discount_rounding",
    "quantity_x_price",
    "noisy_footer",
    "bad_spacing",
)


def main() -> None:
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=42)
    for name in FIXTURE_NAMES:
        lines = (FIXTURE_ROOT / f"{name}.txt").read_text(encoding="utf-8").splitlines()
        image = Image.new("RGB", (1800, max(300, 90 + 68 * len(lines))), "white")
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(lines):
            draw.text((80, 45 + index * 68), line, fill="black", font=font)
        image.save(IMAGE_ROOT / f"{name}.png", format="PNG", optimize=False)

    sample = Image.open(IMAGE_ROOT / "sample_restaurant_expected.png").convert("RGB")
    sample.rotate(-4, expand=True, fillcolor="white").save(
        IMAGE_ROOT / "sample_rotated.png", format="PNG", optimize=False
    )
    ImageEnhance.Contrast(sample).enhance(0.2).save(
        IMAGE_ROOT / "sample_low_contrast.png", format="PNG", optimize=False
    )
    sample.filter(ImageFilter.GaussianBlur(radius=1.6)).save(
        IMAGE_ROOT / "sample_blurred.png", format="PNG", optimize=False
    )
    sample.crop((0, 0, sample.width, sample.height - 75)).save(
        IMAGE_ROOT / "sample_cropped_total.png", format="PNG", optimize=False
    )


if __name__ == "__main__":
    main()
