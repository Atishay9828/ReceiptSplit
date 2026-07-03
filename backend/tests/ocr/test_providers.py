from __future__ import annotations

import asyncio

import pytest

from app.ocr.contracts import OcrImageInput
from app.ocr.errors import OcrProviderTimeout, OcrProviderUnavailable
from app.ocr.providers import MockOcrProvider, TesseractOcrProvider


async def test_mock_provider_returns_fixture_text() -> None:
    provider = MockOcrProvider("Tea 10.00")

    result = await provider.extract_text(
        OcrImageInput(content=b"image", content_type="image/png", width=1, height=1)
    )

    assert result.raw_text == "Tea 10.00"
    assert result.provider == "mock"


async def test_tesseract_provider_missing_binary_maps_to_domain_error() -> None:
    provider = TesseractOcrProvider(tesseract_cmd="definitely-missing-tesseract", timeout_seconds=1)

    with pytest.raises(OcrProviderUnavailable):
        await provider.extract_text(
            OcrImageInput(content=b"image", content_type="image/png", width=1, height=1)
        )


async def test_tesseract_provider_timeout_maps_to_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HangingProcess:
        async def communicate(self, _: bytes) -> tuple[bytes, bytes]:
            await asyncio.sleep(10)
            return b"", b""

        def kill(self) -> None:
            return None

    async def fake_create_subprocess_exec(*_: object, **__: object) -> HangingProcess:
        return HangingProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    provider = TesseractOcrProvider(tesseract_cmd="tesseract", timeout_seconds=0.01)

    with pytest.raises(OcrProviderTimeout):
        await provider.extract_text(
            OcrImageInput(content=b"image", content_type="image/png", width=1, height=1)
        )
