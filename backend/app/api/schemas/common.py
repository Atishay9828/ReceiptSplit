from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class OKResponse(BaseModel):
    ok: bool = True


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
