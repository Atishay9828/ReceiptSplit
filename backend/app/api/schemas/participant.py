from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.common import ORMModel
from app.shared.validators import strip_html


class JoinRoomRequest(BaseModel):
    invite_token: str = Field(min_length=1)
    nickname: str = Field(min_length=1, max_length=30)
    color: str | None = Field(default=None)

    @field_validator("nickname", mode="before")
    @classmethod
    def sanitize_nickname(cls, v: str) -> str:
        if isinstance(v, str):
            return strip_html(v)
        return v


class ParticipantResponse(ORMModel):
    id: UUID
    room_id: UUID
    user_id: UUID | None
    nickname: str
    color: str
    role: str
    joined_at: datetime


class JoinRoomResponse(BaseModel):
    participant: ParticipantResponse
    participant_token: str
