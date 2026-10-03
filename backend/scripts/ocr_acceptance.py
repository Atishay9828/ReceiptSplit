"""Run the pinned Tesseract engine against independent receipt expectations."""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import os
from pathlib import Path

from app.ocr.contracts import OcrImageInput, ParsedReceiptDraft
from app.ocr.parser import IndianRestaurantReceiptParser
from app.ocr.preprocessing import BasicReceiptPreprocessor
from app.ocr.providers import TesseractOcrProvider

FIXTURE_ROOT = Path(os.environ.get("RECEIPTSPLIT_FIXTURE_ROOT", "/fixtures"))
EXPECTED_ROOT = FIXTURE_ROOT / "expected"
IMAGE_ROOT = FIXTURE_ROOT / "images"
REAL_RECEIPTS_ROOT = Path(os.environ.get("RECEIPTSPLIT_REAL_RECEIPTS_ROOT", "/real-receipts"))
CLEAR_FIXTURES = (
    "sample_restaurant_expected",
    "simple_restaurant",
    "gst_cgst_sgst",
    "discount_rounding",
    "quantity_x_price",
    "noisy_footer",
    "bad_spacing",
)
REAL_FIXTURES = (
    ("sample_restaurant_photo", "sample_restaurant.jpg"),
    ("riverside_bistro_photo", "riverside_bistro.png"),
)
DEGRADED_FIXTURES = (
    "sample_rotated",
    "sample_low_contrast",
    "sample_blurred",
    "sample_cropped_total",
)
COMPARE_FIELDS = (
    "merchant_name",
    "subtotal_paise",
    "tax_paise",
    "discount_paise",
    "total_paise",
    "items",
    "adjustments",
    "warnings",
    "needs_review",
)


def _comparison(draft: ParsedReceiptDraft) -> dict[str, object]:
    parsed = draft.model_dump(
        mode="json",
        include=set(COMPARE_FIELDS),
        exclude={"items": {"__all__": {"confidence"}}},
    )
    parsed["adjustments"] = [
        {"type": adjustment["type"], "amount_paise": adjustment["amount_paise"]}
        for adjustment in parsed["adjustments"]
    ]
    return parsed


async def _read_and_parse(
    path: Path,
    parser: IndianRestaurantReceiptParser,
    provider: TesseractOcrProvider,
    preprocessor: BasicReceiptPreprocessor,
) -> tuple[dict[str, object], dict[str, object]]:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    preprocessed = await preprocessor.preprocess(path.read_bytes(), content_type)
    result = await provider.extract_text(
        OcrImageInput(
            content=preprocessed.content,
            content_type=preprocessed.content_type,
            width=preprocessed.width,
            height=preprocessed.height,
        )
    )
    if result.provider != "tesseract":
        raise AssertionError(f"Expected Tesseract provider, got {result.provider}")
    draft = parser.parse(result.raw_text)
    return _comparison(draft), preprocessed.metadata


async def run(psm: int) -> int:
    provider = TesseractOcrProvider(language="eng", psm=psm)
    await provider.check_ready()
    parser = IndianRestaurantReceiptParser()
    preprocessor = BasicReceiptPreprocessor()
    failures = 0
    print(f"provider=tesseract language=eng psm={psm} preprocessor=receipt-binarize-v1")

    for name in CLEAR_FIXTURES:
        actual, preprocessing = await _read_and_parse(
            IMAGE_ROOT / f"{name}.png", parser, provider, preprocessor
        )
        expected = json.loads((EXPECTED_ROOT / f"{name}.json").read_text(encoding="utf-8"))
        expected["items"] = [
            {key: value for key, value in item.items() if key != "confidence"}
            for item in expected["items"]
        ]
        expected["adjustments"] = [
            {"type": item["type"], "amount_paise": item["amount_paise"]}
            for item in expected["adjustments"]
        ]
        differences = {
            field: {"expected": expected[field], "actual": actual[field]}
            for field in COMPARE_FIELDS
            if actual[field] != expected[field]
        }
        failures += bool(differences)
        print(
            json.dumps(
                {
                    "fixture": name,
                    "status": "PASS" if not differences else "FAIL",
                    "differences": differences,
                    "preprocessing": preprocessing,
                },
                ensure_ascii=False,
            )
        )

    for name, filename in REAL_FIXTURES:
        actual, preprocessing = await _read_and_parse(
            REAL_RECEIPTS_ROOT / filename, parser, provider, preprocessor
        )
        expected = json.loads((EXPECTED_ROOT / f"{name}.json").read_text(encoding="utf-8"))
        expected["items"] = [
            {key: value for key, value in item.items() if key != "confidence"}
            for item in expected["items"]
        ]
        expected["adjustments"] = [
            {"type": item["type"], "amount_paise": item["amount_paise"]}
            for item in expected["adjustments"]
        ]
        differences = {
            field: {"expected": expected[field], "actual": actual[field]}
            for field in COMPARE_FIELDS
            if actual[field] != expected[field]
        }
        failures += bool(differences)
        print(
            json.dumps(
                {
                    "fixture": name,
                    "status": "PASS" if not differences else "FAIL",
                    "differences": differences,
                    "preprocessing": preprocessing,
                },
                ensure_ascii=False,
            )
        )

    expected_sample = json.loads(
        (EXPECTED_ROOT / "sample_restaurant_expected.json").read_text(encoding="utf-8")
    )
    for name in DEGRADED_FIXTURES:
        actual, preprocessing = await _read_and_parse(
            IMAGE_ROOT / f"{name}.png", parser, provider, preprocessor
        )
        expected_items = [
            {key: value for key, value in item.items() if key != "confidence"}
            for item in expected_sample["items"]
        ]
        exact = all(
            actual[field] == expected_value
            for field, expected_value in (
                ("merchant_name", expected_sample["merchant_name"]),
                ("subtotal_paise", expected_sample["subtotal_paise"]),
                ("tax_paise", expected_sample["tax_paise"]),
                ("discount_paise", expected_sample["discount_paise"]),
                ("total_paise", expected_sample["total_paise"]),
                ("items", expected_items),
                ("adjustments", expected_sample["adjustments"]),
            )
        )
        reviewed = actual["needs_review"] or actual["total_paise"] is None
        passed = exact or reviewed
        failures += not passed
        print(
            json.dumps(
                {
                    "fixture": name,
                    "status": "PASS" if passed else "FAIL",
                    "outcome": "exact" if exact else "review_required" if reviewed else "unflagged_mismatch",
                    "actual": actual,
                    "preprocessing": preprocessing,
                },
                ensure_ascii=False,
            )
        )
    return int(failures > 0)


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "--psm",
        type=int,
        default=int(os.environ.get("RECEIPTSPLIT_TESSERACT_PSM", "4")),
    )
    arguments = argument_parser.parse_args()
    raise SystemExit(asyncio.run(run(arguments.psm)))
