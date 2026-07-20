from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from sqlalchemy import select

from app.models.abuse_report import AbuseReport
from app.models.audit_log import AuditLog
from tests.api.conftest import bearer
from tests.api.test_settlement import _participant_request, _prepared_room

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def _audit_actions(db_session: AsyncSession) -> list[str]:
    result = await db_session.execute(select(AuditLog.action).order_by(AuditLog.created_at))
    return list(result.scalars().all())


async def test_settlement_actions_are_rate_limited_and_audited(
    api_client: Any, db_session: AsyncSession
) -> None:
    data = await _prepared_room(api_client)
    room_id = data["room"]["id"]
    request_id = _participant_request(data["settlement"])["id"]

    opened = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/open-payment",
        headers=bearer(data["participant_token"]),
    )
    assert opened.status_code == 200

    for _ in range(10):
        limited = await api_client.post(
            f"/api/rooms/{room_id}/settlement/requests/{request_id}/open-payment",
            headers=bearer(data["participant_token"]),
        )

    assert limited.status_code == 429
    assert limited.json() == {
        "error": {
            "code": "RATE_LIMITED",
            "message": "Too many attempts. Please try again later.",
        }
    }

    actions = await _audit_actions(db_session)
    assert "settlement.payment_opened" in actions
    assert "suspicious.flagged" in actions


async def test_claim_confirm_and_dispute_create_audit_entries(
    api_client: Any, db_session: AsyncSession
) -> None:
    data = await _prepared_room(api_client)
    room_id = data["room"]["id"]
    request_id = _participant_request(data["settlement"])["id"]

    claimed = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/claim-paid",
        headers=bearer(data["participant_token"]),
    )
    assert claimed.status_code == 200

    disputed = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/dispute",
        json={"reason": "<b>not mine</b>\x00"},
        headers=bearer(data["creator_token"]),
    )
    assert disputed.status_code == 200

    reclaimed = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/claim-paid",
        headers=bearer(data["participant_token"]),
    )
    assert reclaimed.status_code == 200

    confirmed = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/confirm",
        headers=bearer(data["creator_token"]),
    )
    assert confirmed.status_code == 200

    actions = await _audit_actions(db_session)
    assert "settlement.claimed_paid" in actions
    assert "settlement.disputed" in actions
    assert "settlement.payer_confirmed" in actions


async def test_payer_vpa_change_after_prepare_is_blocked_and_audited(
    api_client: Any, db_session: AsyncSession
) -> None:
    data = await _prepared_room(api_client)
    room_id = data["room"]["id"]

    response = await api_client.put(
        f"/api/rooms/{room_id}/settlement/payer",
        json={"payee_vpa": "bait.switch@upi", "payee_name": "Changed"},
        headers=bearer(data["creator_token"]),
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == (
        "Payer details cannot be changed after settlement requests are prepared."
    )

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "settlement.payer_details_change_blocked")
    )
    audit = result.scalars().one()
    assert str(audit.room_id) == data["room"]["id"]
    assert audit.event_metadata["attempted_payee_vpa_fingerprint"]
    assert "bait.switch@upi" not in str(audit.event_metadata)


async def test_abuse_report_is_sanitized_rate_limited_and_does_not_store_token(
    api_client: Any, db_session: AsyncSession
) -> None:
    data = await _prepared_room(api_client)
    room_id = data["room"]["id"]

    response = await api_client.post(
        f"/api/rooms/{room_id}/abuse-reports",
        json={"reason": "wrong_payee", "message": "<script>x</script>\x00Check VPA"},
        headers=bearer(data["participant_token"]),
    )
    assert response.status_code == 201
    assert response.json()["reason"] == "wrong_payee"
    assert "<script>" not in response.json()["message"]

    for _ in range(5):
        limited = await api_client.post(
            f"/api/rooms/{room_id}/abuse-reports",
            json={"reason": "spam", "message": "again"},
            headers=bearer(data["participant_token"]),
        )

    assert limited.status_code == 429

    reports = (await db_session.execute(select(AbuseReport))).scalars().all()
    assert len(reports) == 5
    assert all("rs_pt_" not in str(cast("Any", report).__dict__) for report in reports)

    actions = await _audit_actions(db_session)
    assert "abuse.reported" in actions


async def test_invalid_invite_token_is_audited_without_raw_token(
    api_client: Any, db_session: AsyncSession
) -> None:
    data = await _prepared_room(api_client)
    room_id = data["room"]["id"]
    raw_token = "rs_inv_this-raw-token-must-not-be-stored"

    response = await api_client.post(
        f"/api/rooms/{room_id}/join",
        json={"invite_token": raw_token, "nickname": "Mallory"},
    )

    assert response.status_code == 403
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "token.access_failed")
    )
    audit = result.scalars().one()
    assert str(audit.room_id) == data["room"]["id"]
    assert raw_token not in str(audit.event_metadata)
    assert "token_fingerprint" in audit.event_metadata
