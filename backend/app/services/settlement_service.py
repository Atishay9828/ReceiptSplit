from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from app.domain.settlement import (
    SettlementAmountError,
    SettlementForbiddenError,
    SettlementLink,
    SettlementLinkBuilder,
    SettlementNotReadyError,
    SettlementRequestNotFoundError,
    SettlementStatus,
    assert_settlement_transition,
    format_paise_as_rupees,
    validate_payer_details,
)
from app.models.participant_total import ParticipantTotal
from app.models.room_participant import RoomParticipant
from app.models.settlement_request import SettlementRequest
from app.models.settlement_status_event import SettlementStatusEvent
from app.security.safe import sanitize_text
from app.shared.errors import RoomNotFound

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.context import AuthenticatedUser, ParticipantAuthContext
    from app.models.room import Room
    from app.models.split_session import SplitSession
    from app.repositories.interfaces.room import RoomRepository
    from app.repositories.interfaces.split_session import SplitSessionRepository
    from app.services.audit_service import AuditService
    from app.services.event_publisher import EventPublisher


SETTLEMENT_DISCLAIMER = (
    "Check the recipient UPI ID and amount inside your UPI app before paying. "
    'ReceiptSplit does not verify bank transfer. Mark "I paid" only after completing payment.'
)


@dataclass(frozen=True, slots=True)
class SettlementActor:
    participant: ParticipantAuthContext | None = None
    user: AuthenticatedUser | None = None

    @property
    def actor_id(self) -> UUID | None:
        if self.participant is not None:
            return self.participant.participant_id
        if self.user is not None:
            return self.user.id
        return None

    @property
    def actor_participant_id(self) -> UUID | None:
        return self.participant.participant_id if self.participant is not None else None

    @property
    def actor_user_id(self) -> UUID | None:
        return self.user.id if self.user is not None else None

    @property
    def is_creator(self) -> bool:
        return bool(self.participant and self.participant.is_creator) or (
            self.user is not None and self.participant is None
        )


@dataclass(frozen=True, slots=True)
class OpenPaymentResult:
    request: SettlementRequest
    link: SettlementLink
    amount_paise: int
    disclaimer: str = SETTLEMENT_DISCLAIMER


class SettlementService:
    def __init__(
        self,
        room_repo: RoomRepository,
        session_repo: SplitSessionRepository,
        event_publisher: EventPublisher,
        audit_service: AuditService | None = None,
        link_builder: SettlementLinkBuilder | None = None,
    ) -> None:
        self._room_repo = room_repo
        self._session_repo = session_repo
        self._events = event_publisher
        self._audit = audit_service
        self._links = link_builder or SettlementLinkBuilder()

    async def configure_payer_details(
        self,
        db: AsyncSession,
        *,
        room_id: UUID,
        actor: SettlementActor,
        payee_vpa: str,
        payee_name: str,
    ) -> Room:
        if not actor.is_creator:
            raise SettlementForbiddenError()
        normalized_vpa, normalized_name = validate_payer_details(payee_vpa, payee_name)

        async with db.begin_nested():
            room = await self._room_repo.get_by_id(db, room_id)
            if room is None:
                raise RoomNotFound()

            if await self._has_requests(db, room_id) and room.payer_vpa != normalized_vpa:
                raise SettlementNotReadyError(
                    "Payer details cannot be changed after settlement requests are prepared."
                )

            room.payer_vpa = normalized_vpa
            room.payer_name = normalized_name
            room.version += 1
            room.updated_at = datetime.now(UTC)
            await db.flush()
            await self._events.append_in_tx(
                db,
                room_id,
                "settlement.payer_configured",
                actor.actor_id,
                {"payer_details_configured": True},
            )
            if self._audit is not None:
                await self._audit.record(
                    db,
                    action="settlement.payer_details_set",
                    room_id=room_id,
                    actor_participant_id=actor.actor_participant_id,
                    actor_user_id=actor.actor_user_id,
                    actor_type="creator",
                    metadata={"payee_vpa_fingerprint": self._fingerprint(normalized_vpa)},
                )
        return room

    async def prepare_settlement_requests(
        self,
        db: AsyncSession,
        *,
        room_id: UUID,
        actor: SettlementActor,
    ) -> list[SettlementRequest]:
        if not actor.is_creator:
            raise SettlementForbiddenError()

        async with db.begin_nested():
            room = await self._room_repo.get_by_id(db, room_id)
            if room is None:
                raise RoomNotFound()
            if room.status not in {"settling", "settled"}:
                raise SettlementNotReadyError("Lock the bill before preparing settlement.")
            if not room.payer_vpa or not room.payer_name:
                raise SettlementNotReadyError("Save payout details before preparing settlement.")
            payee_vpa, payee_name = validate_payer_details(room.payer_vpa, room.payer_name)

            session = await self._session_repo.get_by_room(db, room_id)
            if session is None:
                raise SettlementNotReadyError("Locked participant totals are missing.")

            totals = await self._list_settleable_totals(db, session)
            if not totals:
                raise SettlementNotReadyError("No participant owes a positive amount.")

            existing = await self._list_requests(db, room_id)
            existing_by_participant = {request.participant_id: request for request in existing}
            created: list[SettlementRequest] = []
            for total in totals:
                if total.participant_id in existing_by_participant:
                    continue
                request = SettlementRequest(
                    room_id=room_id,
                    split_session_id=session.id,
                    participant_id=total.participant_id,
                    amount_paise=total.total_paise,
                    payee_vpa=payee_vpa,
                    payee_name=payee_name,
                    payment_reference=self._reference(room_id, total.participant_id),
                    status=SettlementStatus.DUE.value,
                )
                db.add(request)
                await db.flush()
                await self._insert_status_event(
                    db,
                    request=request,
                    actor=actor,
                    old_status=None,
                    new_status=SettlementStatus.DUE,
                )
                created.append(request)

            await self._events.append_in_tx(
                db,
                room_id,
                "settlement.requests_prepared",
                actor.actor_id,
                {"created_count": len(created), "request_count": len(existing) + len(created)},
            )
            if self._audit is not None:
                await self._audit.record(
                    db,
                    action="settlement.requests_prepared",
                    room_id=room_id,
                    actor_participant_id=actor.actor_participant_id,
                    actor_user_id=actor.actor_user_id,
                    actor_type="creator",
                    metadata={
                        "created_count": len(created),
                        "request_count": len(existing) + len(created),
                    },
                )

        return await self._list_requests(db, room_id)

    async def get_settlement_summary(
        self,
        db: AsyncSession,
        *,
        room_id: UUID,
        actor: SettlementActor,
    ) -> list[SettlementRequest]:
        if actor.is_creator:
            return await self._list_requests(db, room_id)
        if actor.participant is None or actor.participant.room_id != room_id:
            raise SettlementForbiddenError()
        return await self._list_requests(
            db, room_id, participant_id=actor.participant.participant_id
        )

    async def has_settlement_requests(self, db: AsyncSession, room_id: UUID) -> bool:
        return await self._has_requests(db, room_id)

    async def open_payment(
        self,
        db: AsyncSession,
        *,
        room_id: UUID,
        request_id: UUID,
        actor: SettlementActor,
        amount_paise: int | None = None,
    ) -> OpenPaymentResult:
        request = await self._get_own_participant_request(db, room_id, request_id, actor)
        old_status = SettlementStatus(request.status)
        if old_status in {SettlementStatus.DUE, SettlementStatus.DISPUTED}:
            request = await self._transition(
                db,
                request=request,
                actor=actor,
                new_status=SettlementStatus.PAYMENT_OPENED,
                event_type="settlement.payment_opened",
                timestamp_field="opened_at",
            )
        elif self._audit is not None:
            await self._audit.record(
                db,
                action="settlement.payment_opened",
                room_id=room_id,
                participant_id=request.participant_id,
                actor_participant_id=actor.actor_participant_id,
                actor_user_id=actor.actor_user_id,
                actor_type="participant",
                metadata={
                    "settlement_request_id": str(request.id),
                    "status": request.status,
                },
            )

        if self._audit is not None:
            count = await self._audit.count_recent_by_metadata(
                db,
                action="settlement.payment_opened",
                key="settlement_request_id",
                value=str(request.id),
            )
            if count >= 3:
                await self._audit.record(
                    db,
                    action="suspicious.flagged",
                    room_id=room_id,
                    participant_id=request.participant_id,
                    actor_participant_id=actor.actor_participant_id,
                    actor_user_id=actor.actor_user_id,
                    actor_type="participant",
                    metadata={
                        "flag": "repeated_payment_opened",
                        "settlement_request_id": str(request.id),
                        "count": count,
                    },
                )
        payment_amount = self._validated_payment_amount(request, amount_paise)
        link = self._links.build(
            payee_vpa=request.payee_vpa,
            payee_name=request.payee_name,
            amount_paise=payment_amount,
            reference=request.payment_reference,
        )
        return OpenPaymentResult(request=request, link=link, amount_paise=payment_amount)

    async def claim_paid(
        self,
        db: AsyncSession,
        *,
        room_id: UUID,
        request_id: UUID,
        actor: SettlementActor,
        amount_paise: int | None = None,
    ) -> SettlementRequest:
        request = await self._get_own_participant_request(db, room_id, request_id, actor)
        remaining_before = self.remaining_amount_paise(request)
        claimed_amount = self._validated_payment_amount(request, amount_paise)
        request.pending_claim_amount_paise = claimed_amount
        return await self._transition(
            db,
            request=request,
            actor=actor,
            new_status=SettlementStatus.CLAIMED_PAID,
            event_type="settlement.claimed_paid",
            timestamp_field="claimed_paid_at",
            event_metadata={
                "claimed_amount_paise": claimed_amount,
                "remaining_before_paise": remaining_before,
            },
        )

    async def confirm_paid(
        self,
        db: AsyncSession,
        *,
        room_id: UUID,
        request_id: UUID,
        actor: SettlementActor,
    ) -> SettlementRequest:
        if not actor.is_creator:
            raise SettlementForbiddenError()
        request = await self._get_request(db, room_id, request_id)
        claimed_amount = request.pending_claim_amount_paise
        if claimed_amount is None or request.status != SettlementStatus.CLAIMED_PAID.value:
            raise SettlementNotReadyError("There is no payment claim waiting for confirmation.")
        request.confirmed_amount_paise += claimed_amount
        request.pending_claim_amount_paise = None
        remaining_after = self.remaining_amount_paise(request)
        new_status = (
            SettlementStatus.PAYER_CONFIRMED
            if remaining_after == 0
            else SettlementStatus.DUE
        )
        return await self._transition(
            db,
            request=request,
            actor=actor,
            new_status=new_status,
            event_type="settlement.payer_confirmed",
            timestamp_field="payer_confirmed_at" if remaining_after == 0 else None,
            event_metadata={
                "confirmed_amount_paise": claimed_amount,
                "total_confirmed_paise": request.confirmed_amount_paise,
                "remaining_after_paise": remaining_after,
            },
        )

    async def dispute_payment(
        self,
        db: AsyncSession,
        *,
        room_id: UUID,
        request_id: UUID,
        actor: SettlementActor,
        reason: str | None = None,
    ) -> SettlementRequest:
        if not actor.is_creator:
            raise SettlementForbiddenError()
        request = await self._get_request(db, room_id, request_id)
        disputed_amount = request.pending_claim_amount_paise
        request.pending_claim_amount_paise = None
        return await self._transition(
            db,
            request=request,
            actor=actor,
            new_status=SettlementStatus.DISPUTED,
            event_type="settlement.disputed",
            timestamp_field="disputed_at",
            reason=sanitize_text(reason, max_length=300),
            event_metadata={"disputed_amount_paise": disputed_amount}
            if disputed_amount is not None
            else {},
        )

    async def _transition(
        self,
        db: AsyncSession,
        *,
        request: SettlementRequest,
        actor: SettlementActor,
        new_status: SettlementStatus,
        event_type: str,
        timestamp_field: str | None,
        reason: str | None = None,
        event_metadata: dict[str, object] | None = None,
    ) -> SettlementRequest:
        async with db.begin_nested():
            old_status = SettlementStatus(request.status)
            assert_settlement_transition(old_status, new_status)
            request.status = new_status.value
            request.updated_at = datetime.now(UTC)
            request.version += 1
            if timestamp_field is not None:
                setattr(request, timestamp_field, request.updated_at)
            await db.flush()
            await self._insert_status_event(
                db,
                request=request,
                actor=actor,
                old_status=old_status,
                new_status=new_status,
                reason=reason,
                event_metadata=event_metadata,
            )
            await self._events.append_in_tx(
                db,
                request.room_id,
                event_type,
                actor.actor_id,
                {
                    "settlement_request_id": str(request.id),
                    "participant_id": str(request.participant_id),
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    **(event_metadata or {}),
                },
            )
            if self._audit is not None:
                await self._audit.record(
                    db,
                    action=event_type,
                    room_id=request.room_id,
                    participant_id=request.participant_id,
                    actor_participant_id=actor.actor_participant_id,
                    actor_user_id=actor.actor_user_id,
                    actor_type="creator" if actor.is_creator else "participant",
                    metadata={
                        "settlement_request_id": str(request.id),
                        "old_status": old_status.value,
                        "new_status": new_status.value,
                        "reason_present": bool(reason),
                        **(event_metadata or {}),
                    },
                )

            # Auto-settle check: if new_status is PAYER_CONFIRMED, check if all are confirmed
            if new_status == SettlementStatus.PAYER_CONFIRMED:
                requests = await self._list_requests(db, request.room_id)
                if all(r.status == SettlementStatus.PAYER_CONFIRMED.value for r in requests):
                    room = await self._room_repo.get_by_id(db, request.room_id)
                    if room and room.status == "settling":
                        room.status = "settled"
                        room.version += 1
                        await db.flush()

                        await self._events.append_in_tx(
                            db,
                            request.room_id,
                            "room.state_changed",
                            actor_id=actor.actor_id,
                            payload={"from": "settling", "to": "settled", "auto": True},
                        )
                        if self._audit is not None:
                            await self._audit.record(
                                db,
                                action="room.state_changed",
                                room_id=request.room_id,
                                actor_participant_id=actor.actor_participant_id,
                                actor_user_id=actor.actor_user_id,
                                actor_type="creator" if actor.is_creator else "participant",
                                metadata={"from": "settling", "to": "settled", "auto": True},
                            )
                        # We also need to emit it to the websocket
                        await self._events.broadcast(
                            request.room_id,
                            "room.state_changed",
                            {"from": "settling", "to": "settled", "auto": True},
                        )

        return request

    async def _insert_status_event(
        self,
        db: AsyncSession,
        *,
        request: SettlementRequest,
        actor: SettlementActor,
        old_status: SettlementStatus | None,
        new_status: SettlementStatus,
        reason: str | None = None,
        event_metadata: dict[str, Any] | None = None,
    ) -> None:
        db.add(
            SettlementStatusEvent(
                settlement_request_id=request.id,
                room_id=request.room_id,
                participant_id=request.participant_id,
                actor_participant_id=actor.actor_participant_id,
                actor_user_id=actor.actor_user_id,
                old_status=old_status.value if old_status is not None else None,
                new_status=new_status.value,
                reason=reason,
                event_metadata=event_metadata or {},
            )
        )

    async def _get_own_participant_request(
        self,
        db: AsyncSession,
        room_id: UUID,
        request_id: UUID,
        actor: SettlementActor,
    ) -> SettlementRequest:
        if actor.participant is None or actor.participant.is_creator:
            raise SettlementForbiddenError()
        request = await self._get_request(db, room_id, request_id)
        if request.participant_id != actor.participant.participant_id:
            raise SettlementForbiddenError()
        return request

    async def _get_request(
        self,
        db: AsyncSession,
        room_id: UUID,
        request_id: UUID,
    ) -> SettlementRequest:
        stmt = (
            select(SettlementRequest)
            .where(
                SettlementRequest.id == request_id,
                SettlementRequest.room_id == room_id,
            )
            .with_for_update()
        )
        result = await db.execute(stmt)
        request = result.scalars().first()
        if request is None:
            raise SettlementRequestNotFoundError()
        return request

    async def _list_requests(
        self,
        db: AsyncSession,
        room_id: UUID,
        participant_id: UUID | None = None,
    ) -> list[SettlementRequest]:
        stmt = select(SettlementRequest).where(SettlementRequest.room_id == room_id)
        if participant_id is not None:
            stmt = stmt.where(SettlementRequest.participant_id == participant_id)
        result = await db.execute(
            stmt.order_by(SettlementRequest.created_at, SettlementRequest.id)
        )
        return list(result.scalars().all())

    async def _has_requests(self, db: AsyncSession, room_id: UUID) -> bool:
        stmt = select(func.count(SettlementRequest.id)).where(SettlementRequest.room_id == room_id)
        result = await db.execute(stmt)
        return int(result.scalar_one()) > 0

    async def _list_settleable_totals(
        self,
        db: AsyncSession,
        session: SplitSession,
    ) -> list[ParticipantTotal]:
        stmt = (
            select(ParticipantTotal)
            .join(RoomParticipant, RoomParticipant.id == ParticipantTotal.participant_id)
            .where(
                ParticipantTotal.split_session_id == session.id,
                ParticipantTotal.is_payer.is_(False),
                ParticipantTotal.total_paise > 0,
                RoomParticipant.left_at.is_(None),
            )
            .order_by(RoomParticipant.joined_at, RoomParticipant.id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def amount_display(request: SettlementRequest) -> str:
        return format_paise_as_rupees(request.amount_paise)

    @staticmethod
    def remaining_amount_paise(request: SettlementRequest) -> int:
        return request.amount_paise - request.confirmed_amount_paise

    @classmethod
    def remaining_amount_display(cls, request: SettlementRequest) -> str:
        remaining = cls.remaining_amount_paise(request)
        return "0.00" if remaining == 0 else format_paise_as_rupees(remaining)

    @classmethod
    def _validated_payment_amount(
        cls, request: SettlementRequest, amount_paise: int | None
    ) -> int:
        remaining = cls.remaining_amount_paise(request)
        if request.pending_claim_amount_paise is not None:
            raise SettlementNotReadyError(
                "Wait for the payer to confirm or dispute the current payment claim."
            )
        chosen = remaining if amount_paise is None else amount_paise
        if chosen <= 0:
            raise SettlementAmountError(remaining_paise=remaining)
        if chosen > remaining:
            raise SettlementAmountError(
                "Payment claim cannot exceed the remaining balance.",
                remaining_paise=remaining,
            )
        return chosen

    @staticmethod
    def _reference(room_id: UUID, participant_id: UUID) -> str:
        return f"RS-{room_id.hex[:8].upper()}-{participant_id.hex[:8].upper()}"

    @staticmethod
    def _fingerprint(value: str) -> str:
        from app.security.safe import fingerprint

        result = fingerprint(value)
        return result or ""
