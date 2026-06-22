from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.api.schemas.common import ORMModel

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class RoomCreateRequest(BaseModel):
    split_mode: str = Field(default="equal", pattern="^(equal|item_wise)$")


class RoomUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    status: str | None = Field(default=None, pattern="^(draft|active|settling|settled|archived|expired)$")
    split_mode: str | None = Field(default=None, pattern="^(equal|item_wise)$")
    payer_vpa: str | None = Field(default=None, max_length=50)
    payer_name: str | None = Field(default=None, max_length=100)


class RoomResponse(ORMModel):
    id: UUID
    status: str
    split_mode: str
    payer_vpa: str | None
    payer_name: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class RoomCreateResponse(BaseModel):
    room: RoomResponse
    creator_token: str
    invite_token: str
