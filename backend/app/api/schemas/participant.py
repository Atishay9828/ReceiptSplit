from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.api.schemas.common import ORMModel

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class JoinRoomRequest(BaseModel):
    invite_token: str = Field(min_length=1)
    nickname: str = Field(min_length=1, max_length=30)
    color: str = Field(pattern="^#[0-9A-Fa-f]{6}$")


class ParticipantResponse(ORMModel):
    id: UUID
    room_id: UUID
    nickname: str
    color: str
    role: str
    joined_at: datetime


class JoinRoomResponse(BaseModel):
    participant: ParticipantResponse
    participant_token: str
