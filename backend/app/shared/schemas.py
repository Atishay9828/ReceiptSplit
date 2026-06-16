"""
ReceiptSplit — Shared API Schemas

Common Pydantic response and error models used across all routers.
These are not domain models — they are API transport shapes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Matches PDD §16.1 API error format."""

    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Outer wrapper for all error responses."""

    error: ErrorDetail


class OKResponse(BaseModel):
    """Generic success response for operations that return no data."""

    ok: bool = True
