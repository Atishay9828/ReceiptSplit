from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.errors import ERROR_RESPONSES
from app.api.schemas.settlement import (
    DisputeSettlementRequest,
    OpenPaymentResponse,
    PayerDetailsRequest,
    SettlementAggregates,
    SettlementRequestResponse,
    SettlementSummaryResponse,
)
from app.auth.dependencies import (
    require_room_access,
    require_room_event_access,
    require_room_owner_or_creator,
)
from app.database import get_db
from app.domain.settlement import SettlementNotReadyError
from app.security.rate_limit import RateLimitRule, client_host, enforce_rate_limit
from app.security.safe import fingerprint
from app.services.registry import get_audit_service, get_room_service, get_settlement_service
from app.services.settlement_service import SettlementActor, SettlementService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.dependencies import AuthorizedRoomActor
    from app.auth.models import AuthContext, RequestAuthContext
    from app.models.room import Room
    from app.models.settlement_request import SettlementRequest
    from app.services.audit_service import AuditService
    from app.services.room_service import RoomService


router = APIRouter(
    prefix="/api/rooms/{room_id}/settlement",
    tags=["settlement"],
    responses=ERROR_RESPONSES,
)


@router.get("", summary="Get settlement summary", response_model=SettlementSummaryResponse)
async def get_settlement(
    room_id: UUID,
    ctx: RequestAuthContext = Depends(require_room_event_access),
    db: AsyncSession = Depends(get_db),
    room_service: RoomService = Depends(get_room_service),
    service: SettlementService = Depends(get_settlement_service),
) -> SettlementSummaryResponse:
    room = await room_service.get_room(db, room_id)
    requests = await service.get_settlement_summary(
        db,
        room_id=room_id,
        actor=SettlementActor(
            participant=ctx.participant,
            user=ctx.user if ctx.participant is None else None,
        ),
    )
    return _summary(room, requests)


@router.put("/payer", summary="Configure payer details", response_model=SettlementSummaryResponse)
async def configure_payer(
    room_id: UUID,
    payload: PayerDetailsRequest,
    request: Request,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: SettlementService = Depends(get_settlement_service),
    audit: AuditService = Depends(get_audit_service),
) -> SettlementSummaryResponse:
    enforce_rate_limit(
        request,
        action="settlement.payer_details_update",
        key_parts=[str(room_id), str(actor.actor_id), client_host(request)],
        rule=RateLimitRule(limit=5, window_seconds=3600),
    )
    try:
        room = await service.configure_payer_details(
            db,
            room_id=room_id,
            actor=SettlementActor(participant=actor.participant, user=actor.user),
            payee_vpa=payload.payee_vpa,
            payee_name=payload.payee_name,
        )
    except SettlementNotReadyError as exc:
        if (
            exc.message
            != "Payer details cannot be changed after settlement requests are prepared."
        ):
            raise
        await audit.record(
            db,
            action="settlement.payer_details_change_blocked",
            room_id=room_id,
            actor_participant_id=actor.participant.participant_id if actor.participant else None,
            actor_user_id=actor.user.id if actor.user else None,
            actor_type="creator",
            metadata={
                "attempted_payee_vpa_fingerprint": fingerprint(payload.payee_vpa),
            },
            request=request,
        )
        return JSONResponse(status_code=422, content={"error": exc.to_dict()})  # type: ignore[return-value]
    requests = await service.get_settlement_summary(
        db,
        room_id=room_id,
        actor=SettlementActor(participant=actor.participant, user=actor.user),
    )
    return _summary(room, requests)


@router.post(
    "/prepare",
    status_code=status.HTTP_201_CREATED,
    summary="Prepare settlement requests",
    response_model=SettlementSummaryResponse,
)
async def prepare_settlement(
    room_id: UUID,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    room_service: RoomService = Depends(get_room_service),
    service: SettlementService = Depends(get_settlement_service),
) -> SettlementSummaryResponse:
    requests = await service.prepare_settlement_requests(
        db,
        room_id=room_id,
        actor=SettlementActor(participant=actor.participant, user=actor.user),
    )
    room = await room_service.get_room(db, room_id)
    return _summary(room, requests)


@router.post(
    "/requests/{request_id}/open-payment",
    summary="Open participant payment",
    response_model=OpenPaymentResponse,
)
async def open_payment(
    room_id: UUID,
    request_id: UUID,
    http_request: Request,
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    service: SettlementService = Depends(get_settlement_service),
) -> OpenPaymentResponse:
    enforce_rate_limit(
        http_request,
        action="settlement.open_payment",
        key_parts=[str(request_id), str(ctx.participant_id), client_host(http_request)],
        rule=RateLimitRule(limit=10, window_seconds=600),
    )
    result = await service.open_payment(
        db,
        room_id=room_id,
        request_id=request_id,
        actor=SettlementActor(participant=ctx),
    )
    return OpenPaymentResponse(
        settlement_request_id=result.request.id,
        status=result.request.status,
        amount_paise=result.request.amount_paise,
        amount_display=result.link.amount_display,
        payee_vpa=result.link.payee_vpa,
        payee_name=result.link.payee_name,
        payment_reference=result.link.payment_reference,
        upi_uri=result.link.upi_uri,
        qr_payload=result.link.qr_payload,
        copy_vpa=result.link.payee_vpa,
        disclaimer=result.disclaimer,
    )


@router.post(
    "/requests/{request_id}/claim-paid",
    summary="Claim payment completed",
    response_model=SettlementRequestResponse,
)
async def claim_paid(
    room_id: UUID,
    request_id: UUID,
    http_request: Request,
    ctx: AuthContext = Depends(require_room_access),
    db: AsyncSession = Depends(get_db),
    service: SettlementService = Depends(get_settlement_service),
) -> SettlementRequestResponse:
    enforce_rate_limit(
        http_request,
        action="settlement.claim_paid",
        key_parts=[str(request_id), str(ctx.participant_id)],
        rule=RateLimitRule(limit=10, window_seconds=3600),
    )
    settlement_request = await service.claim_paid(
        db,
        room_id=room_id,
        request_id=request_id,
        actor=SettlementActor(participant=ctx),
    )
    return _request_response(settlement_request)


@router.post(
    "/requests/{request_id}/confirm",
    summary="Confirm payment manually",
    response_model=SettlementRequestResponse,
)
async def confirm_paid(
    room_id: UUID,
    request_id: UUID,
    http_request: Request,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: SettlementService = Depends(get_settlement_service),
) -> SettlementRequestResponse:
    enforce_rate_limit(
        http_request,
        action="settlement.confirm",
        key_parts=[str(room_id), str(actor.actor_id)],
        rule=RateLimitRule(limit=60, window_seconds=3600),
    )
    settlement_request = await service.confirm_paid(
        db,
        room_id=room_id,
        request_id=request_id,
        actor=SettlementActor(participant=actor.participant, user=actor.user),
    )
    return _request_response(settlement_request)


@router.post(
    "/requests/{request_id}/dispute",
    summary="Mark payment disputed",
    response_model=SettlementRequestResponse,
)
async def dispute_payment(
    room_id: UUID,
    request_id: UUID,
    http_request: Request,
    payload: DisputeSettlementRequest | None = None,
    actor: AuthorizedRoomActor = Depends(require_room_owner_or_creator),
    db: AsyncSession = Depends(get_db),
    service: SettlementService = Depends(get_settlement_service),
) -> SettlementRequestResponse:
    enforce_rate_limit(
        http_request,
        action="settlement.dispute",
        key_parts=[str(room_id), str(actor.actor_id)],
        rule=RateLimitRule(limit=60, window_seconds=3600),
    )
    settlement_request = await service.dispute_payment(
        db,
        room_id=room_id,
        request_id=request_id,
        actor=SettlementActor(participant=actor.participant, user=actor.user),
        reason=payload.reason if payload is not None else None,
    )
    return _request_response(settlement_request)


def _summary(room: Room, requests: list[SettlementRequest]) -> SettlementSummaryResponse:
    return SettlementSummaryResponse(
        room_id=room.id,
        payer_details_configured=bool(room.payer_vpa and room.payer_name),
        payee_vpa=room.payer_vpa,
        payee_name=room.payer_name,
        requests=[_request_response(request) for request in requests],
        aggregates=_aggregates(requests),
    )


def _request_response(request: SettlementRequest) -> SettlementRequestResponse:
    return SettlementRequestResponse(
        id=request.id,
        room_id=request.room_id,
        participant_id=request.participant_id,
        amount_paise=request.amount_paise,
        amount_display=SettlementService.amount_display(request),
        currency=request.currency,
        payee_vpa=request.payee_vpa,
        payee_name=request.payee_name,
        payment_reference=request.payment_reference,
        status=request.status,
        created_at=request.created_at,
        updated_at=request.updated_at,
        opened_at=request.opened_at,
        claimed_paid_at=request.claimed_paid_at,
        payer_confirmed_at=request.payer_confirmed_at,
        disputed_at=request.disputed_at,
    )


def _aggregates(requests: list[SettlementRequest]) -> SettlementAggregates:
    counts = {
        "due": 0,
        "payment_opened": 0,
        "claimed_paid": 0,
        "payer_confirmed": 0,
        "disputed": 0,
    }
    total_confirmed = 0
    for request in requests:
        counts[request.status] += 1
        if request.status == "payer_confirmed":
            total_confirmed += request.amount_paise
    return SettlementAggregates(
        due_count=counts["due"],
        payment_opened_count=counts["payment_opened"],
        claimed_paid_count=counts["claimed_paid"],
        payer_confirmed_count=counts["payer_confirmed"],
        disputed_count=counts["disputed"],
        total_due_paise=sum(request.amount_paise for request in requests),
        total_confirmed_paise=total_confirmed,
    )
