from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

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
class OcrTextToken:
    """One recognized word and its image-space geometry."""

    text: str
    confidence: float | None
    page_num: int
    block_num: int
    paragraph_num: int
    line_num: int
    word_num: int
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class OcrProviderResult:
    provider: str
    raw_text: str
    confidence: float | None = None
    tokens: tuple[OcrTextToken, ...] = ()
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class ParsedReceiptLine(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=999)
    unit_price_paise: int | None = Field(default=None, ge=0)
    total_paise: int = Field(ge=0, le=10_000_000)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ParsedReceiptAdjustment(BaseModel):
    type: Literal[
        "tax",
        "service_charge",
        "delivery_fee",
        "packaging_fee",
        "tip",
        "discount",
        "coupon",
        "offer",
        "adjustment",
        "rounding",
    ]
    label: str = Field(min_length=1, max_length=100)
    amount_paise: int = Field(gt=-10_000_000, le=10_000_000)
    allocation_method: Literal["proportional", "equal"] = "proportional"


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
        """Extract ordered text and optional layout evidence from a receipt image."""
        ...


class ImagePreprocessor(Protocol):
    async def preprocess(self, image: bytes, content_type: str) -> PreprocessedImage:
        """Return normalized image bytes ready for OCR."""
        ...


class ReceiptParser(Protocol):
    def parse(self, raw_text: str) -> ParsedReceiptDraft:
        """Parse raw OCR text into a user-reviewable draft."""
        ...
