from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.abuse_report import AbuseReport
from app.security.safe import sanitize_text

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import RequestAuthContext
    from app.services.audit_service import AuditService


class AbuseService:
    def __init__(self, audit_service: AuditService) -> None:
        self._audit = audit_service

    async def report(
        self,
        db: AsyncSession,
        *,
        room_id: UUID,
        ctx: RequestAuthContext,
        reason: str,
        message: str | None,
    ) -> AbuseReport:
        reporter_role = "unknown"
        reporter_participant_id = None
        reporter_user_id = None
        if ctx.participant is not None:
            reporter_participant_id = ctx.participant.participant_id
            reporter_role = "creator" if ctx.participant.is_creator else "participant"
        if ctx.user is not None:
            reporter_user_id = ctx.user.id
            reporter_role = "creator"

        clean_message = sanitize_text(message, max_length=500)
        report = AbuseReport(
            room_id=room_id,
            reporter_participant_id=reporter_participant_id,
            reporter_user_id=reporter_user_id,
            reporter_role=reporter_role,
            reason=reason,
            message=clean_message,
        )
        db.add(report)
        await db.flush()
        await self._audit.record(
            db,
            action="abuse.reported",
            room_id=room_id,
            actor_participant_id=reporter_participant_id,
            actor_user_id=reporter_user_id,
            actor_type=reporter_role,
            metadata={"reason": reason, "message_present": bool(clean_message)},
        )
        return report
