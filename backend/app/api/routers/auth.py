from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.room import RoomResponse
from app.auth.dependencies import require_authenticated_user
from app.database import get_db
from app.repositories.postgres.room import PostgresRoomRepository
from app.repositories.postgres.user import PostgresUserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import AuthenticatedUser


class AuthMeResponse(BaseModel):
    id: UUID
    provider: str
    subject: str
    email: str | None
    username: str | None
    display_name: str | None


class UserRoomsResponse(BaseModel):
    rooms: list[RoomResponse]


router = APIRouter(tags=["auth"], responses=ERROR_RESPONSES)
_room_repo = PostgresRoomRepository()


@router.get(
    "/api/auth/me",
    summary="Get authenticated user",
    response_model=AuthMeResponse,
)
async def get_me(
    user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> AuthMeResponse:
    local_user = await PostgresUserRepository().get_by_id(db, user.id)
    return AuthMeResponse(
        id=user.id,
        provider=user.provider,
        subject=user.subject,
        email=user.email,
        username=local_user.username if local_user else None,
        display_name=local_user.display_name if local_user else None,
    )


@router.get(
    "/api/users/me/rooms",
    summary="List authenticated user's rooms",
    response_model=UserRoomsResponse,
)
async def get_my_rooms(
    user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> UserRoomsResponse:
    rooms = await _room_repo.list_by_creator(db, user.id)
    return UserRoomsResponse(rooms=[RoomResponse.model_validate(room) for room in rooms])
