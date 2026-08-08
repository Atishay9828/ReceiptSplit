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


async def test_mock_provider_default_is_receipt_like() -> None:
    provider = MockOcrProvider()

    result = await provider.extract_text(
        OcrImageInput(content=b"image", content_type="image/png", width=1, height=1)
    )

    assert "ReceiptSplit Cafe" in result.raw_text
    assert "TOTAL 441.00" in result.raw_text
    assert result.provider == "mock"


async def test_tesseract_provider_missing_binary_maps_to_domain_error() -> None:
    provider = TesseractOcrProvider(
        tesseract_cmd="definitely-missing-tesseract", timeout_seconds=1
    )

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


async def test_tesseract_provider_preserves_tsv_tokens_and_reconstructs_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tsv = (
        b"level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        b"5\t1\t1\t1\t1\t1\t10\t20\t100\t20\t96.5\tTea\n"
        b"5\t1\t1\t1\t1\t2\t120\t20\t40\t20\t91.0\t10.00\n"
        b"5\t1\t1\t1\t2\t1\t10\t50\t80\t20\t88.0\tTOTAL\n"
        b"5\t1\t1\t1\t2\t2\t120\t50\t40\t20\t90.0\t10.00\n"
    )

    class CompletedProcess:
        returncode = 0

        async def communicate(self, _: bytes) -> tuple[bytes, bytes]:
            return tsv, b""

    command: tuple[object, ...] = ()

    async def fake_create_subprocess_exec(*args: object, **__: object) -> CompletedProcess:
        nonlocal command
        command = args
        return CompletedProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    provider = TesseractOcrProvider(language="eng", psm=4)

    result = await provider.extract_text(
        OcrImageInput(content=b"image", content_type="image/png", width=200, height=100)
    )

    assert result.raw_text == "Tea 10.00\nTOTAL 10.00"
    assert [token.text for token in result.tokens] == ["Tea", "10.00", "TOTAL", "10.00"]
    assert result.tokens[0].left == 10
    assert result.tokens[0].confidence == pytest.approx(0.965)
    assert result.confidence == pytest.approx((0.965 + 0.91 + 0.88 + 0.9) / 4)
    assert command[-5:] == ("-l", "eng", "--psm", "4", "tsv")
    assert result.provider_metadata["output_format"] == "tsv"


def test_tesseract_provider_rejects_invalid_page_segmentation_mode() -> None:
    with pytest.raises(ValueError, match="between 0 and 13"):
        TesseractOcrProvider(psm=14)


async def test_tesseract_provider_cancellation_kills_child_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()

    class CancellableProcess:
        returncode = 0

        def __init__(self) -> None:
            self.killed = False

        async def communicate(self, _: bytes) -> tuple[bytes, bytes]:
            started.set()
            await asyncio.Event().wait()
            return b"", b""

        def kill(self) -> None:
            self.killed = True

    process = CancellableProcess()

    async def fake_create_subprocess_exec(*_: object, **__: object) -> CancellableProcess:
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    task = asyncio.create_task(
        TesseractOcrProvider().extract_text(
            OcrImageInput(content=b"image", content_type="image/png", width=1, height=1)
        )
    )
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.killed is True
