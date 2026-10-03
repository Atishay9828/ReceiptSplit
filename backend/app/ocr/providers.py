from __future__ import annotations

import asyncio
import csv
import io
import re

from app.ocr.contracts import OcrImageInput, OcrProviderResult, OcrTextToken
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
    def __init__(
        self,
        tesseract_cmd: str = "tesseract",
        timeout_seconds: float = 30.0,
        language: str | None = None,
        psm: int = 4,
    ) -> None:
        if not 0 <= psm <= 13:
            raise ValueError("Tesseract page segmentation mode must be between 0 and 13")
        self._cmd = tesseract_cmd
        self._timeout_seconds = timeout_seconds
        self._language = language
        self._psm = psm

    async def check_ready(self) -> None:
        try:
            process = await asyncio.create_subprocess_exec(
                self._cmd,
                "--list-langs",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise RuntimeError("Tesseract executable is unavailable") from None
        try:
            stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError("Tesseract language check timed out") from None
        if process.returncode != 0:
            raise RuntimeError("Tesseract language check failed")
        languages = {line.strip() for line in stdout.decode("utf-8", errors="replace").splitlines()}
        if self._language and self._language not in languages:
            raise RuntimeError(f"Tesseract language data is missing: {self._language}")

    async def extract_text(self, image: OcrImageInput) -> OcrProviderResult:
        command = [
            self._cmd,
            "stdin",
            "stdout",
        ]
        if self._language:
            command.extend(["-l", self._language])
        command.extend(["--psm", str(self._psm), "tsv"])
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
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
            wait = getattr(process, "wait", None)
            if wait is not None:
                await wait()
            raise OcrProviderTimeout("tesseract") from None
        except asyncio.CancelledError:
            process.kill()
            wait = getattr(process, "wait", None)
            if wait is not None:
                await wait()
            raise

        if getattr(process, "returncode", 0) not in (0, None):
            raise OcrProviderFailed("tesseract")

        raw_text, tokens, decimal_separator_reconstructed = _parse_tesseract_tsv(stdout)
        if not raw_text.strip():
            raise OcrProviderFailed("tesseract")
        token_confidences = [token.confidence for token in tokens if token.confidence is not None]
        return OcrProviderResult(
            provider="tesseract",
            raw_text=raw_text,
            confidence=(sum(token_confidences) / len(token_confidences))
            if token_confidences
            else None,
            tokens=tokens,
            provider_metadata={
                "stderr": stderr.decode("utf-8", errors="replace")[:500],
                "content_type": image.content_type,
                "output_format": "tsv",
                "psm": self._psm,
                "language": self._language,
                "decimal_separator_reconstructed": decimal_separator_reconstructed,
            },
        )


def _parse_tesseract_tsv(
    output: bytes,
) -> tuple[str, tuple[OcrTextToken, ...], bool]:
    """Convert Tesseract TSV into ordered text and bounded layout evidence."""
    reader = csv.DictReader(io.StringIO(output.decode("utf-8", errors="replace")), delimiter="\t")
    required_columns = {
        "level",
        "page_num",
        "block_num",
        "par_num",
        "line_num",
        "word_num",
        "left",
        "top",
        "width",
        "height",
        "conf",
        "text",
    }
    if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
        raise OcrProviderFailed("tesseract")

    tokens: list[OcrTextToken] = []
    for row in reader:
        if row.get("level") != "5":
            continue
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            token = OcrTextToken(
                text=text,
                confidence=_parse_confidence(row.get("conf")),
                page_num=_parse_nonnegative_int(row.get("page_num")),
                block_num=_parse_nonnegative_int(row.get("block_num")),
                paragraph_num=_parse_nonnegative_int(row.get("par_num")),
                line_num=_parse_nonnegative_int(row.get("line_num")),
                word_num=_parse_nonnegative_int(row.get("word_num")),
                left=_parse_nonnegative_int(row.get("left")),
                top=_parse_nonnegative_int(row.get("top")),
                width=_parse_nonnegative_int(row.get("width")),
                height=_parse_nonnegative_int(row.get("height")),
            )
        except (TypeError, ValueError):
            continue
        tokens.append(token)

    token_lines: list[list[OcrTextToken]] = []
    current_key: tuple[int, int, int, int] | None = None
    current_tokens: list[OcrTextToken] = []
    for token in tokens:
        key = (token.page_num, token.block_num, token.paragraph_num, token.line_num)
        if current_key is not None and key != current_key:
            token_lines.append(current_tokens)
            current_tokens = []
        current_key = key
        current_tokens.append(token)
    if current_tokens:
        token_lines.append(current_tokens)

    lines: list[str] = []
    decimal_separator_reconstructed = False
    for line_tokens in token_lines:
        words: list[str] = []
        previous_token: OcrTextToken | None = None
        for token in line_tokens:
            if previous_token is not None and _is_split_decimal_fragment(previous_token, token):
                words[-1] = f"{words[-1]}.{token.text}"
                decimal_separator_reconstructed = True
            else:
                words.append(token.text)
            previous_token = token
        lines.append(" ".join(words))
    return "\n".join(lines), tuple(tokens), decimal_separator_reconstructed


def _is_split_decimal_fragment(
    previous: OcrTextToken, token: OcrTextToken
) -> bool:
    if not previous.text.rstrip()[-1:].isdigit():
        return False
    previous_integer = previous.text.rstrip().rsplit(" ", maxsplit=1)[-1]
    if not re.fullmatch(r"[^\d]*\d{2,}", previous_integer):
        return False
    if not re.fullmatch(r"\d{2}", token.text):
        return False
    line_height = min(previous.height, token.height)
    if line_height <= 0:
        return False
    gap = token.left - (previous.left + previous.width)
    vertical_center_delta = abs(
        (previous.top + previous.height / 2) - (token.top + token.height / 2)
    )
    return (
        -line_height * 0.15 <= gap <= line_height * 0.75
        and vertical_center_delta <= line_height * 0.4
    )


def _parse_confidence(value: str | None) -> float | None:
    if value is None or value.strip() in {"", "-1"}:
        return None
    confidence = float(value) / 100
    if not 0 <= confidence <= 1:
        raise ValueError("invalid confidence")
    return confidence


def _parse_nonnegative_int(value: str | None) -> int:
    if value is None:
        raise ValueError("missing integer")
    parsed = int(value)
    if parsed < 0:
        raise ValueError("negative integer")
    return parsed
