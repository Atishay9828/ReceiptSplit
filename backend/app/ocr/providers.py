from __future__ import annotations

import asyncio

from app.ocr.contracts import OcrImageInput, OcrProviderResult
from app.ocr.errors import OcrProviderFailed, OcrProviderTimeout, OcrProviderUnavailable

DEFAULT_MOCK_RECEIPT_TEXT = """ReceiptSplit Cafe
Paneer Tikka 240.00
Masala Dosa 180.00
CGST 10.50
SGST 10.50
TOTAL 441.00"""


class MockOcrProvider:
    def __init__(self, fixture_text: str = DEFAULT_MOCK_RECEIPT_TEXT) -> None:
        self._fixture_text = fixture_text

    async def extract_text(self, image: OcrImageInput) -> OcrProviderResult:
        return OcrProviderResult(
            provider="mock",
            raw_text=self._fixture_text,
            confidence=1.0,
            provider_metadata={
                "width": image.width,
                "height": image.height,
                "content_type": image.content_type,
            },
        )


class TesseractOcrProvider:
    def __init__(self, tesseract_cmd: str = "tesseract", timeout_seconds: float = 30.0) -> None:
        self._cmd = tesseract_cmd
        self._timeout_seconds = timeout_seconds

    async def extract_text(self, image: OcrImageInput) -> OcrProviderResult:
        try:
            process = await asyncio.create_subprocess_exec(
                self._cmd,
                "stdin",
                "stdout",
                "--psm",
                "6",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise OcrProviderUnavailable("tesseract") from None

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(image.content), timeout=self._timeout_seconds
            )
        except TimeoutError:
            process.kill()
            raise OcrProviderTimeout("tesseract") from None

        if getattr(process, "returncode", 0) not in (0, None):
            raise OcrProviderFailed("tesseract")

        return OcrProviderResult(
            provider="tesseract",
            raw_text=stdout.decode("utf-8", errors="replace").strip(),
            confidence=None,
            provider_metadata={
                "stderr": stderr.decode("utf-8", errors="replace")[:500],
                "content_type": image.content_type,
            },
        )
