from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, status

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.community import (
    CommunityUserResponse,
    FriendAddRequest,
    FriendsResponse,
    GroupBillCreateRequest,
    GroupBillCreateResponse,
    GroupBillSummaryResponse,
    GroupCreateRequest,
    GroupMemberResponse,
    GroupResponse,
    GroupsResponse,
    ProfileUpdateRequest,
)
from app.api.schemas.room import RoomCreateResponse, RoomResponse
from app.auth.dependencies import require_authenticated_user
from app.database import get_db
from app.services.registry import get_community_service, get_room_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import AuthenticatedUser
    from app.models.group import Group
    from app.models.user import User
    from app.services.community_service import CommunityService
    from app.services.room_service import RoomService


router = APIRouter(tags=["community"], responses=ERROR_RESPONSES)


def user_response(user: User) -> CommunityUserResponse:
    return CommunityUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
    )


async def build_group_response(
    db: AsyncSession,
    service: CommunityService,
    group: Group,
    role: str,
    user: AuthenticatedUser,
) -> GroupResponse:
    members = await service.group_members(db, group.id)
    bills = await service.group_bills(db, group.id, user.id)
    bill_responses = [
        GroupBillSummaryResponse(
            id=row["room"].id,
            title=row["room"].title or "Untitled bill",
            status=row["room"].status,
            created_at=row["room"].created_at,
            grand_total_paise=row["grand_total_paise"],
            pending_paise=row["pending_paise"],
            cleared_paise=row["cleared_paise"],
            current_participant_id=row["current_participant_id"],
            is_creator=row["room"].creator_user_id == user.id,
        )
        for row in bills
    ]
    return GroupResponse(
        id=group.id,
        name=group.name,
        role=role,
        members=[
            GroupMemberResponse(
                **user_response(member).model_dump(),
                role=member_role,
            )
            for member, member_role in members
        ],
        bills=bill_responses,
        total_paise=sum(bill.grand_total_paise for bill in bill_responses),
        pending_paise=sum(bill.pending_paise for bill in bill_responses),
        cleared_paise=sum(bill.cleared_paise for bill in bill_responses),
        created_at=group.created_at,
    )


@router.put("/api/users/me/profile", response_model=CommunityUserResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    service: CommunityService = Depends(get_community_service),
) -> CommunityUserResponse:
    updated = await service.update_profile(
        db, user.id, username=payload.username, display_name=payload.display_name
    )
    return user_response(updated)


@router.get("/api/users/me/friends", response_model=FriendsResponse)
async def list_friends(
    user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    service: CommunityService = Depends(get_community_service),
) -> FriendsResponse:
    friends = await service.list_friends(db, user.id)
    return FriendsResponse(friends=[user_response(friend) for friend in friends])


@router.post(
    "/api/users/me/friends",
    status_code=status.HTTP_201_CREATED,
    response_model=CommunityUserResponse,
)
async def add_friend(
    payload: FriendAddRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    service: CommunityService = Depends(get_community_service),
) -> CommunityUserResponse:
    friend = await service.add_friend(db, user.id, payload.username)
    return user_response(friend)


@router.get("/api/groups", response_model=GroupsResponse)
async def list_groups(
    user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    service: CommunityService = Depends(get_community_service),
) -> GroupsResponse:
    rows = await service.group_rows(db, user.id)
    return GroupsResponse(
        groups=[await build_group_response(db, service, group, role, user) for group, role in rows]
    )


@router.post("/api/groups", status_code=status.HTTP_201_CREATED, response_model=GroupResponse)
async def create_group(
    payload: GroupCreateRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    service: CommunityService = Depends(get_community_service),
) -> GroupResponse:
    group = await service.create_group(
        db, user.id, name=payload.name, member_usernames=payload.member_usernames
    )
    return await build_group_response(db, service, group, "owner", user)


@router.post(
    "/api/groups/{group_id}/bills",
    status_code=status.HTTP_201_CREATED,
    response_model=GroupBillCreateResponse,
)
async def create_group_bill(
    group_id: UUID,
    payload: GroupBillCreateRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    community: CommunityService = Depends(get_community_service),
    rooms: RoomService = Depends(get_room_service),
) -> GroupBillCreateResponse:
    room, creator_token, invite_token = await community.create_bill(
        db,
        rooms,
        group_id=group_id,
        user_id=user.id,
        title=payload.title,
        split_mode=payload.split_mode,
        payer_name=payload.payer_name,
        payer_vpa=payload.payer_vpa,
    )
    return GroupBillCreateResponse(
        bill=RoomCreateResponse(
            room=RoomResponse.model_validate(room),
            creator_token=creator_token,
            invite_token=invite_token,
        )
    )
