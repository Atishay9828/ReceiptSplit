from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.security.safe import fingerprint

if TYPE_CHECKING:
    from uuid import UUID

    from fastapi import Request
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import AuthenticatedUser


class AuditService:
    async def record(
        self,
        db: AsyncSession,
        *,
        action: str,
        room_id: UUID | None = None,
        participant_id: UUID | None = None,
        actor_participant_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        actor_type: str = "unknown",
        metadata: dict[str, Any] | None = None,
        request: Request | None = None,
        user: AuthenticatedUser | None = None,
    ) -> AuditLog:
        if user is not None:
            actor_user_id = user.id
            actor_type = "user"

        log = AuditLog(
            action=action,
            room_id=room_id,
            participant_id=participant_id,
            actor_participant_id=actor_participant_id,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            ip_fingerprint=fingerprint(
                request.client.host if request and request.client else None
            ),
            user_agent=(request.headers.get("user-agent", "")[:200] if request else None),
            event_metadata=metadata or {},
        )
        db.add(log)
        await db.flush()
        return log

    async def count_recent_by_metadata(
        self,
        db: AsyncSession,
        *,
        action: str,
        key: str,
        value: str,
    ) -> int:
        stmt = select(func.count(AuditLog.id)).where(
            AuditLog.action == action,
            AuditLog.event_metadata[key].as_string() == value,
        )
        result = await db.execute(stmt)
        return int(result.scalar_one())
