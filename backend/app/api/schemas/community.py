from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.room import RoomCreateResponse  # noqa: TC001
from app.shared.validators import strip_html


class ProfileUpdateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=30, pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return strip_html(value).strip().lower()

    @field_validator("display_name", mode="before")
    @classmethod
    def sanitize_display_name(cls, value: str) -> str:
        return strip_html(value).strip()


class CommunityUserResponse(BaseModel):
    id: UUID
    username: str | None
    display_name: str | None


class FriendAddRequest(BaseModel):
    username: str = Field(min_length=2, max_length=30)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return strip_html(value).strip().lower()


class FriendsResponse(BaseModel):
    friends: list[CommunityUserResponse]


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    member_usernames: list[str] = Field(default_factory=list, max_length=19)

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        return strip_html(value).strip()

    @field_validator("member_usernames")
    @classmethod
    def normalize_members(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip().lower() for value in values if value.strip()))


class GroupBillCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    split_mode: str = Field(default="item_wise", pattern="^(equal|item_wise)$")
    payer_name: str | None = Field(default=None, max_length=100)
    payer_vpa: str | None = Field(default=None, max_length=50)

    @field_validator("title", mode="before")
    @classmethod
    def sanitize_title(cls, value: str) -> str:
        return strip_html(value).strip()


class GroupMemberResponse(CommunityUserResponse):
    role: str


class GroupBillSummaryResponse(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime
    grand_total_paise: int
    pending_paise: int
    cleared_paise: int
    current_participant_id: UUID | None
    is_creator: bool


class GroupResponse(BaseModel):
    id: UUID
    name: str
    role: str
    members: list[GroupMemberResponse]
    bills: list[GroupBillSummaryResponse]
    total_paise: int
    pending_paise: int
    cleared_paise: int
    created_at: datetime


class GroupsResponse(BaseModel):
    groups: list[GroupResponse]


class GroupBillCreateResponse(BaseModel):
    bill: RoomCreateResponse
