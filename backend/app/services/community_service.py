from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import and_, func, or_, select

from app.auth.tokens import generate_participant_token, hash_token
from app.models.friendship import Friendship
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.participant_total import ParticipantTotal
from app.models.room import Room
from app.models.room_participant import RoomParticipant
from app.models.settlement_request import SettlementRequest
from app.models.split_session import SplitSession
from app.models.user import User
from app.shared.errors import DomainError, NotAuthorized

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.room_service import RoomService


class GroupBillRow(TypedDict):
    room: Room
    grand_total_paise: int
    pending_paise: int
    cleared_paise: int
    current_participant_id: UUID | None


class CommunityService:
    async def update_profile(
        self, db: AsyncSession, user_id: UUID, *, username: str, display_name: str
    ) -> User:
        existing = await db.execute(
            select(User).where(func.lower(User.username) == username.lower(), User.id != user_id)
        )
        if existing.scalars().first() is not None:
            raise DomainError(code="USERNAME_TAKEN", message="That username is already in use.")
        user = await db.get(User, user_id)
        if user is None:
            raise DomainError(code="USER_NOT_FOUND", message="Account not found.")
        user.username = username.lower()
        user.display_name = display_name
        await db.flush()
        return user

    async def add_friend(self, db: AsyncSession, user_id: UUID, username: str) -> User:
        result = await db.execute(select(User).where(func.lower(User.username) == username.lower()))
        friend = result.scalars().first()
        if friend is None:
            raise DomainError(code="USER_NOT_FOUND", message="No account uses that username.")
        if friend.id == user_id:
            raise DomainError(code="INVALID_FRIEND", message="You cannot add yourself.")
        low_id, high_id = sorted((user_id, friend.id), key=str)
        existing = await db.execute(
            select(Friendship).where(
                Friendship.user_low_id == low_id,
                Friendship.user_high_id == high_id,
            )
        )
        if existing.scalars().first() is None:
            db.add(Friendship(user_low_id=low_id, user_high_id=high_id))
            await db.flush()
        return friend

    async def list_friends(self, db: AsyncSession, user_id: UUID) -> list[User]:
        friendships = await db.execute(
            select(Friendship).where(
                or_(Friendship.user_low_id == user_id, Friendship.user_high_id == user_id)
            )
        )
        friend_ids = [
            row.user_high_id if row.user_low_id == user_id else row.user_low_id
            for row in friendships.scalars().all()
        ]
        if not friend_ids:
            return []
        result = await db.execute(select(User).where(User.id.in_(friend_ids)).order_by(User.username))
        return list(result.scalars().all())

    async def create_group(
        self, db: AsyncSession, user_id: UUID, *, name: str, member_usernames: list[str]
    ) -> Group:
        friends = await self.list_friends(db, user_id)
        friends_by_username = {friend.username: friend for friend in friends if friend.username}
        missing = [username for username in member_usernames if username not in friends_by_username]
        if missing:
            raise DomainError(
                code="FRIEND_REQUIRED",
                message=f"Add these usernames as friends first: {', '.join(missing)}",
            )
        group = Group(name=name, creator_user_id=user_id)
        db.add(group)
        await db.flush()
        db.add(GroupMember(group_id=group.id, user_id=user_id, role="owner"))
        for username in member_usernames:
            db.add(GroupMember(group_id=group.id, user_id=friends_by_username[username].id))
        await db.flush()
        return group

    async def require_group_member(
        self, db: AsyncSession, group_id: UUID, user_id: UUID, *, owner: bool = False
    ) -> GroupMember:
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
        )
        member = result.scalars().first()
        if member is None or (owner and member.role != "owner"):
            raise NotAuthorized()
        return member

    async def create_bill(
        self,
        db: AsyncSession,
        room_service: RoomService,
        *,
        group_id: UUID,
        user_id: UUID,
        title: str,
        split_mode: str,
        payer_name: str | None,
        payer_vpa: str | None,
    ) -> tuple[Room, str, str]:
        await self.require_group_member(db, group_id, user_id, owner=True)
        room, creator_token, invite_token = await room_service.create_room(
            db,
            split_mode=split_mode,
            payer_name=payer_name,
            payer_vpa=payer_vpa,
            title=title,
            group_id=group_id,
            room_ttl_days=3650,
        )
        room.creator_user_id = user_id
        creator = await db.execute(
            select(RoomParticipant).where(
                RoomParticipant.room_id == room.id,
                RoomParticipant.role == "creator",
            )
        )
        creator_participant = creator.scalars().one()
        creator_participant.user_id = user_id

        members = await db.execute(
            select(User)
            .join(GroupMember, GroupMember.user_id == User.id)
            .where(GroupMember.group_id == group_id, User.id != user_id)
        )
        for member in members.scalars().all():
            token = generate_participant_token()
            db.add(
                RoomParticipant(
                    room_id=room.id,
                    user_id=member.id,
                    nickname=member.display_name or member.username or "Friend",
                    color="#2F7D5A",
                    role="participant",
                    token_hash=hash_token(token),
                )
            )
        await db.flush()
        return room, creator_token, invite_token

    async def group_rows(self, db: AsyncSession, user_id: UUID) -> list[tuple[Group, str]]:
        result = await db.execute(
            select(Group, GroupMember.role)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(GroupMember.user_id == user_id, Group.archived_at.is_(None))
            .order_by(Group.created_at.desc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def group_members(self, db: AsyncSession, group_id: UUID) -> list[tuple[User, str]]:
        result = await db.execute(
            select(User, GroupMember.role)
            .join(GroupMember, GroupMember.user_id == User.id)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.role.desc(), GroupMember.joined_at, User.id)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def group_bills(
        self, db: AsyncSession, group_id: UUID, user_id: UUID
    ) -> list[GroupBillRow]:
        result = await db.execute(
            select(Room, SplitSession.id, SplitSession.grand_total_paise, RoomParticipant.id)
            .outerjoin(SplitSession, SplitSession.room_id == Room.id)
            .outerjoin(
                RoomParticipant,
                and_(
                    RoomParticipant.room_id == Room.id,
                    RoomParticipant.user_id == user_id,
                    RoomParticipant.left_at.is_(None),
                ),
            )
            .where(Room.group_id == group_id)
            .order_by(Room.created_at.desc())
        )
        bills: list[GroupBillRow] = []
        for room, split_session_id, grand_total, participant_id in result.all():
            owed = 0
            if split_session_id is not None:
                owed_result = await db.execute(
                    select(func.coalesce(func.sum(ParticipantTotal.total_paise), 0)).where(
                        ParticipantTotal.split_session_id == split_session_id,
                        ParticipantTotal.is_payer.is_(False),
                    )
                )
                owed = int(owed_result.scalar_one() or 0)
            settlement = await db.execute(
                select(
                    func.coalesce(
                        func.sum(SettlementRequest.confirmed_amount_paise),
                        0,
                    ),
                ).where(SettlementRequest.room_id == room.id)
            )
            cleared = int(settlement.scalar_one() or 0)
            bills.append(
                {
                    "room": room,
                    "grand_total_paise": int(grand_total or 0),
                    "pending_paise": max(owed - cleared, 0),
                    "cleared_paise": cleared,
                    "current_participant_id": participant_id,
                }
            )
        return bills
