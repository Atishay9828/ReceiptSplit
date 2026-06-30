"""
ReceiptSplit — Auth FastAPI Dependencies

Provides the dependency chain for route authentication and authorization.

Dependency hierarchy:
  get_current_participant   (resolves token → AuthContext)
       │
  require_room_access       (asserts ctx.room_id == path room_id)  [Amendment API-1]
       │
  require_creator_in_room   (asserts ctx.role == 'creator')

Security invariant (Amendment API-1):
  Every route that has {room_id} in its path MUST use `require_room_access`
  (or `require_creator_in_room`) as its auth dependency.  Using
  `get_current_participant` directly on room-scoped routes is prohibited
  because it does not enforce cross-room token isolation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

if True:
    pass

from typing import TYPE_CHECKING

from fastapi import Depends, Header
from sqlalchemy import text

from app.auth.context import (
    authenticated_user_from_claims,
    classify_bearer_token,
    parse_bearer_authorization,
)
from app.auth.errors import RoomOwnerRequired, UserAuthRequired
from app.auth.models import AuthContext, AuthenticatedUser, RequestAuthContext
from app.auth.provider import get_jwt_verifier
from app.auth.tokens import hash_token
from app.database import get_db
from app.repositories.postgres.room import PostgresRoomRepository
from app.repositories.postgres.user import PostgresUserRepository
from app.shared.errors import InvalidToken, NotAuthorized

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.jwt import JwtVerifier

logger = logging.getLogger(__name__)

_room_repo = PostgresRoomRepository()
_user_repo = PostgresUserRepository()


@dataclass(frozen=True, slots=True)
class AuthorizedRoomActor:
    """Resolved actor for owner-JWT or legacy creator-token mutations."""

    room_id: UUID
    actor_id: UUID
    user: AuthenticatedUser | None = None
    participant: AuthContext | None = None


# ── Core token resolution ──────────────────────────────────────────────────────


async def get_current_participant(
    authorization: str = Header(..., description="Bearer <capability_token>"),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Resolves an Authorization header to an AuthContext.

    Steps:
      1. Extract raw token from 'Bearer <token>' header.
      2. Compute SHA-256(token).
      3. Look up the hash in room_participants.token_hash.
      4. Reject if not found or if participant has left (left_at IS NOT NULL).
      5. Return AuthContext with participant_id, room_id, role.

    Raises:
        InvalidToken: if the token is missing, malformed, not found, or inactive.
    """
    try:
        raw_token = parse_bearer_authorization(authorization)
    except ValueError:
        raise InvalidToken() from None

    return await resolve_participant_auth_context(raw_token, db)


async def resolve_participant_auth_context(raw_token: str, db: AsyncSession) -> AuthContext:
    """Resolve a raw capability token to a participant auth context."""

    token_hash = hash_token(raw_token)

    result = await db.execute(
        text("""
            SELECT id, room_id, role
            FROM   room_participants
            WHERE  token_hash = :token_hash
              AND  left_at    IS NULL
        """),
        {"token_hash": token_hash},
    )
    row = result.first()

    if row is None:
        raise InvalidToken()

    return AuthContext(
        participant_id=UUID(str(row.id)),
        room_id=UUID(str(row.room_id)),
        role=str(row.role),
    )


async def resolve_request_auth_context(
    authorization: str | None,
    db: AsyncSession,
    jwt_verifier: JwtVerifier,
) -> RequestAuthContext:
    """Resolve optional Authorization credentials into separated auth context."""
    if authorization is None:
        return RequestAuthContext()

    try:
        raw_token = parse_bearer_authorization(authorization)
    except ValueError:
        raise InvalidToken() from None

    if classify_bearer_token(raw_token) == "jwt":
        claims = await jwt_verifier.verify(raw_token)
        return RequestAuthContext(user=authenticated_user_from_claims(claims))

    participant = await resolve_participant_auth_context(raw_token, db)
    return RequestAuthContext(participant=participant)


# ── Room-scope enforcement (Amendment API-1) ───────────────────────────────────


async def require_room_access(
    room_id: UUID,
    ctx: AuthContext = Depends(get_current_participant),
) -> AuthContext:
    """
    Security invariant: the authenticated participant must belong to the
    room specified in the URL path.

    This prevents cross-room token reuse.  A valid creator token from Room A
    cannot be used to access Room B's endpoints.

    Raises:
        InvalidToken: if ctx.room_id != path room_id.
    """
    if ctx.room_id != room_id:
        # This should never happen in production — it indicates either
        # a bug in the token issuance logic or a deliberate IDOR attempt.
        logger.critical(
            "SECURITY: cross-room token use detected. token_room=%s path_room=%s participant=%s",
            ctx.room_id,
            room_id,
            ctx.participant_id,
        )
        raise InvalidToken()

    return ctx


async def require_creator_in_room(
    ctx: AuthContext = Depends(require_room_access),
) -> AuthContext:
    """
    Combines room-scope check with creator role check.

    Use this on all creator-only endpoints.

    Raises:
        NotAuthorized: if ctx.role != 'creator'.
    """
    if not ctx.is_creator:
        raise NotAuthorized()
    return ctx


async def get_request_auth_context(
    authorization: str | None = Header(
        default=None, description="Bearer <jwt_or_capability_token>"
    ),
    db: AsyncSession = Depends(get_db),
    jwt_verifier: JwtVerifier = Depends(get_jwt_verifier),
) -> RequestAuthContext:
    """Contract name for resolving optional user JWT and capability auth."""
    ctx = await resolve_request_auth_context(authorization, db, jwt_verifier)
    if ctx.user is None:
        return ctx
    user = await _user_repo.upsert_by_provider_subject(
        db,
        provider=ctx.user.provider,
        subject=ctx.user.subject,
        email=ctx.user.email,
    )
    return RequestAuthContext(
        user=AuthenticatedUser(
            id=user.id,
            provider=user.provider,
            subject=user.subject,
            email=user.email,
        )
    )


async def require_authenticated_user(
    ctx: RequestAuthContext = Depends(get_request_auth_context),
) -> AuthenticatedUser:
    """Contract name for user-only endpoints such as /api/auth/me."""
    if ctx.user is None:
        raise UserAuthRequired()
    return ctx.user


async def require_room_owner_or_creator(
    room_id: UUID,
    ctx: RequestAuthContext = Depends(get_request_auth_context),
    db: AsyncSession = Depends(get_db),
) -> AuthorizedRoomActor:
    """Contract name for owner JWT or legacy creator capability authorization."""
    if ctx.participant is not None:
        if ctx.participant.room_id != room_id:
            logger.critical(
                "SECURITY: cross-room token use detected. "
                "token_room=%s path_room=%s participant=%s",
                ctx.participant.room_id,
                room_id,
                ctx.participant.participant_id,
            )
            raise InvalidToken()
        if not ctx.participant.is_creator:
            raise NotAuthorized()
        return AuthorizedRoomActor(
            room_id=room_id,
            actor_id=ctx.participant.participant_id,
            participant=ctx.participant,
        )

    if ctx.user is not None:
        room = await _room_repo.get_by_id(db, room_id)
        if room is None or room.creator_user_id != ctx.user.id:
            raise RoomOwnerRequired()
        return AuthorizedRoomActor(room_id=room_id, actor_id=ctx.user.id, user=ctx.user)

    raise NotAuthorized()


async def attach_room_owner(room_id: UUID, user: AuthenticatedUser, db: AsyncSession) -> None:
    """Associate a newly created room with its authenticated creator."""
    await _room_repo.attach_creator(db, room_id, user.id)


# ── Event-endpoint combined auth ───────────────────────────────────────────────


async def require_room_event_access(
    room_id: UUID,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    jwt_verifier: JwtVerifier = Depends(get_jwt_verifier),
) -> RequestAuthContext:
    """
    Accepts ANY valid room credential for read access to event endpoints:

      - Participant capability token for this room
      - Creator capability token for this room
      - Owner JWT for this room (authenticated user who created it)

    Rejects:
      - No token
      - Token for a different room
      - Unrelated user JWT (not the room owner)
      - Malformed token / invalid JWT

    Used by:
      GET /api/rooms/{room_id}/events
      GET /api/rooms/{room_id}/events/stream
      GET /api/rooms/{room_id}/events/latest
    """
    if authorization is None:
        raise NotAuthorized()

    ctx = await resolve_request_auth_context(authorization, db, jwt_verifier)

    if ctx.participant is not None:
        # Capability token path: enforce room_id match (cross-room isolation).
        if ctx.participant.room_id != room_id:
            logger.critical(
                "SECURITY: cross-room token on event endpoint. "
                "token_room=%s path_room=%s participant=%s",
                ctx.participant.room_id,
                room_id,
                ctx.participant.participant_id,
            )
            raise InvalidToken()
        return ctx

    if ctx.user is not None:
        # Owner JWT path: user must be the room creator.
        room = await _room_repo.get_by_id(db, room_id)
        if room is None or room.creator_user_id != ctx.user.id:
            raise RoomOwnerRequired()
        return ctx

    raise NotAuthorized()
