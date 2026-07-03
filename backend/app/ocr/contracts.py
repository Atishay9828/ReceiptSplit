from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, Field


@dataclass(frozen=True, slots=True)
class OcrImageInput:
    content: bytes
    content_type: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class PreprocessedImage:
    content: bytes
    content_type: str
    width: int
    height: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OcrProviderResult:
    provider: str
    raw_text: str
    confidence: float | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class ParsedReceiptLine(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=999)
    unit_price_paise: int | None = Field(default=None, ge=0)
    total_paise: int = Field(ge=0, le=10_000_000)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ParsedReceiptAdjustment(BaseModel):
    type: str
    label: str
    amount_paise: int
    allocation_method: str = "proportional"


class ParsedReceiptDraft(BaseModel):
    merchant_name: str | None = None
    subtotal_paise: int | None = Field(default=None, ge=0)
    tax_paise: int | None = Field(default=None, ge=0)
    discount_paise: int | None = None
    total_paise: int | None = Field(default=None, ge=0)
    items: list[ParsedReceiptLine] = Field(default_factory=list)
    adjustments: list[ParsedReceiptAdjustment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    needs_review: bool = True
    parser_version: str = "indian_restaurant_v1"


class OcrProvider(Protocol):
    async def extract_text(self, image: OcrImageInput) -> OcrProviderResult:
        """Extract raw text from a normalized receipt image."""
        ...


class ImagePreprocessor(Protocol):
    async def preprocess(self, image: bytes, content_type: str) -> PreprocessedImage:
        """Return normalized image bytes ready for OCR."""
        ...


class ReceiptParser(Protocol):
    def parse(self, raw_text: str) -> ParsedReceiptDraft:
        """Parse raw OCR text into a user-reviewable draft."""
        ...
