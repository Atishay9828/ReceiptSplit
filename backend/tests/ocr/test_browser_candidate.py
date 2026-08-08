from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas.ocr import BrowserOcrCandidateRequest


def _candidate_payload() -> dict[str, object]:
    return {
        "provider": "paddleocr-js",
        "model": "PP-OCRv5",
        "language": "en",
        "raw_text": "CAFE\nTea 120.00",
        "lines": [
            {
                "text": "CAFE",
                "poly": [
                    {"x": 10, "y": 20},
                    {"x": 100, "y": 20},
                    {"x": 100, "y": 40},
                    {"x": 10, "y": 40},
                ],
                "score": 0.99,
            },
            {
                "text": "Tea 120.00",
                "poly": [
                    {"x": 10, "y": 50},
                    {"x": 180, "y": 50},
                    {"x": 180, "y": 70},
                    {"x": 10, "y": 70},
                ],
                "score": 0.91,
            },
        ],
    }


def test_browser_candidate_becomes_untrusted_provider_result() -> None:
    candidate = BrowserOcrCandidateRequest.model_validate(_candidate_payload())

    result = candidate.to_provider_result()

    assert result.provider == "paddleocr-js"
    assert result.raw_text == "CAFE\nTea 120.00"
    assert result.confidence == pytest.approx(0.95)
    assert [token.text for token in result.tokens] == ["CAFE", "Tea 120.00"]
    assert result.tokens[1].left == 10
    assert result.tokens[1].width == 170
    assert result.provider_metadata == {
        "source": "browser",
        "model": "PP-OCRv5",
        "language": "en",
        "line_count": 2,
    }
    assert "raw_text" not in result.provider_metadata


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "tesseract"),
        ("raw_text", ""),
        ("lines", []),
    ],
)
def test_browser_candidate_rejects_unsupported_or_empty_values(
    field: str, value: object
) -> None:
    payload = _candidate_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        BrowserOcrCandidateRequest.model_validate(payload)


def test_browser_candidate_rejects_coordinates_outside_bound() -> None:
    payload = _candidate_payload()
    payload["lines"] = [
        {
            "text": "CAFE",
            "poly": [
                {"x": 5001, "y": 20},
                {"x": 100, "y": 20},
                {"x": 100, "y": 40},
                {"x": 10, "y": 40},
            ],
            "score": 0.99,
        }
    ]

    with pytest.raises(ValidationError):
        BrowserOcrCandidateRequest.model_validate(payload)
