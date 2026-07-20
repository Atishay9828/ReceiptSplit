from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass

from app.ocr.errors import InvalidReceiptImage

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8"
SUPPORTED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg"}


@dataclass(frozen=True, slots=True)
class ImageValidationConfig:
    max_bytes: int = 5 * 1024 * 1024
    max_width: int = 5000
    max_height: int = 5000
    min_width: int = 1
    min_height: int = 1


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    content_type: str
    width: int
    height: int
    byte_size: int
    sha256: str


class ReceiptImageValidator:
    def __init__(self, config: ImageValidationConfig | None = None) -> None:
        self._config = config or ImageValidationConfig()

    def validate(self, content: bytes, declared_content_type: str) -> ValidatedImage:
        if not content:
            raise InvalidReceiptImage("empty upload")
        if len(content) > self._config.max_bytes:
            raise InvalidReceiptImage("too large")

        content_type = self._sniff_content_type(content)
        normalized_declared = declared_content_type.lower().strip()
        if normalized_declared == "image/jpg":
            normalized_declared = "image/jpeg"
        if content_type not in SUPPORTED_CONTENT_TYPES or normalized_declared not in {
            "image/png",
            "image/jpeg",
        }:
            raise InvalidReceiptImage("unsupported image type")
        if normalized_declared != content_type:
            raise InvalidReceiptImage("content type mismatch")

        width, height = self._dimensions(content, content_type)
        if width < self._config.min_width or height < self._config.min_height:
            raise InvalidReceiptImage("image dimensions are too small")
        if width > self._config.max_width or height > self._config.max_height:
            raise InvalidReceiptImage("image dimensions are too large")

        return ValidatedImage(
            content_type=content_type,
            width=width,
            height=height,
            byte_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def strip_metadata(self, content: bytes, content_type: str) -> bytes:
        if content_type == "image/png":
            return self._strip_png_ancillary_chunks(content)
        if content_type == "image/jpeg":
            return self._strip_jpeg_app_segments(content)
        raise InvalidReceiptImage("unsupported image type")

    def _sniff_content_type(self, content: bytes) -> str:
        if content.startswith(PNG_SIGNATURE):
            return "image/png"
        if content.startswith(JPEG_SIGNATURE):
            return "image/jpeg"
        raise InvalidReceiptImage("unsupported image type")

    def _dimensions(self, content: bytes, content_type: str) -> tuple[int, int]:
        try:
            if content_type == "image/png":
                if len(content) < 24 or not content.startswith(PNG_SIGNATURE):
                    raise ValueError
                return struct.unpack(">II", content[16:24])
            if content_type == "image/jpeg":
                return self._jpeg_dimensions(content)
        except (struct.error, ValueError, IndexError):
            raise InvalidReceiptImage("corrupt image") from None
        raise InvalidReceiptImage("unsupported image type")

    def _jpeg_dimensions(self, content: bytes) -> tuple[int, int]:
        index = 2
        while index + 9 < len(content):
            if content[index] != 0xFF:
                raise ValueError
            marker = content[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            segment_length = int.from_bytes(content[index : index + 2], "big")
            if segment_length < 2:
                raise ValueError
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB}:
                height = int.from_bytes(content[index + 3 : index + 5], "big")
                width = int.from_bytes(content[index + 5 : index + 7], "big")
                return width, height
            index += segment_length
        raise ValueError

    def _strip_png_ancillary_chunks(self, content: bytes) -> bytes:
        if not content.startswith(PNG_SIGNATURE):
            raise InvalidReceiptImage("corrupt image")
        output = bytearray(PNG_SIGNATURE)
        index = len(PNG_SIGNATURE)
        while index + 12 <= len(content):
            length = int.from_bytes(content[index : index + 4], "big")
            chunk_type = content[index + 4 : index + 8]
            chunk_end = index + 12 + length
            if chunk_end > len(content):
                raise InvalidReceiptImage("corrupt image")
            # Critical chunks have an uppercase first byte; ancillary chunks may carry metadata.
            if 65 <= chunk_type[0] <= 90:
                output.extend(content[index:chunk_end])
            index = chunk_end
            if chunk_type == b"IEND":
                break
        return bytes(output)

    def _strip_jpeg_app_segments(self, content: bytes) -> bytes:
        if not content.startswith(JPEG_SIGNATURE):
            raise InvalidReceiptImage("corrupt image")
        output = bytearray(JPEG_SIGNATURE)
        index = 2
        while index < len(content):
            if index + 1 >= len(content) or content[index] != 0xFF:
                output.extend(content[index:])
                break
            marker = content[index + 1]
            if marker == 0xD9:
                output.extend(content[index:])
                break
            if marker == 0xDA:
                output.extend(content[index:])
                break
            if index + 4 > len(content):
                raise InvalidReceiptImage("corrupt image")
            segment_length = int.from_bytes(content[index + 2 : index + 4], "big")
            segment_end = index + 2 + segment_length
            if segment_end > len(content):
                raise InvalidReceiptImage("corrupt image")
            if not 0xE0 <= marker <= 0xEF:
                output.extend(content[index:segment_end])
            index = segment_end
        return bytes(output)
