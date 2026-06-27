
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
from uuid import UUID

if True:
    pass

from typing import TYPE_CHECKING

from fastapi import Depends, Header
from sqlalchemy import text

from app.auth.models import AuthContext, AuthenticatedUser, RequestAuthContext
from app.auth.tokens import extract_bearer_token, hash_token
from app.database import get_db
from app.shared.errors import InvalidToken, NotAuthorized

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


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
        raw_token = extract_bearer_token(authorization)
    except ValueError:
        raise InvalidToken() from None

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
            "SECURITY: cross-room token use detected. "
            "token_room=%s path_room=%s participant=%s",
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


async def get_request_auth_context() -> RequestAuthContext:
    """Contract name for resolving optional user JWT and capability auth."""
    raise NotImplementedError


async def require_authenticated_user(
    ctx: RequestAuthContext = Depends(get_request_auth_context),
) -> AuthenticatedUser:
    """Contract name for user-only endpoints such as /api/auth/me."""
    if ctx.user is None:
        raise NotAuthorized()
    return ctx.user


async def require_room_owner_or_creator(
    room_id: UUID,
    ctx: RequestAuthContext = Depends(get_request_auth_context),
) -> RequestAuthContext:
    """Contract name for owner JWT or legacy creator capability authorization."""
    raise NotImplementedError
