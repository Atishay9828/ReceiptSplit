from __future__ import annotations

from typing import Any, cast

import pytest

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


async def _locked_room(api_client: Any) -> dict[str, Any]:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    room_id = created["room"]["id"]
    creator_token = created["creator_token"]

    room = (
        await api_client.patch(
            f"/api/rooms/{room_id}",
            json={"version": created["room"]["version"], "status": "active"},
            headers=bearer(creator_token),
        )
    ).json()

    joined = (
        await api_client.post(
            f"/api/rooms/{room_id}/join",
            json={"invite_token": created["invite_token"], "nickname": "Bob"},
        )
    ).json()
    item_response = await api_client.post(
        f"/api/rooms/{room_id}/items",
        json={"name": "Burger", "quantity": 1, "total_paise": 1000},
        headers=bearer(creator_token),
    )
    assert item_response.status_code == 201

    lock_response = await api_client.post(
        f"/api/rooms/{room_id}/split/lock",
        json={"version": room["version"]},
        headers=bearer(creator_token),
    )
    assert lock_response.status_code == 201

    return {
        **created,
        "room": room,
        "participant": joined["participant"],
        "participant_token": joined["participant_token"],
    }


async def _prepared_room(api_client: Any) -> dict[str, Any]:
    data = await _locked_room(api_client)
    room_id = data["room"]["id"]
    creator_token = data["creator_token"]

    payer = await api_client.put(
        f"/api/rooms/{room_id}/settlement/payer",
        json={"payee_vpa": "receiptsplit.test@upi", "payee_name": "AJ Payer"},
        headers=bearer(creator_token),
    )
    assert payer.status_code == 200

    prepared = await api_client.post(
        f"/api/rooms/{room_id}/settlement/prepare",
        headers=bearer(creator_token),
    )
    assert prepared.status_code == 201
    data["settlement"] = prepared.json()
    return data


def _participant_request(summary: dict[str, Any]) -> dict[str, Any]:
    requests = cast("list[dict[str, Any]]", summary["requests"])
    assert len(requests) == 1
    return requests[0]


async def test_creator_configures_payer_and_prepares_settlement(api_client: Any) -> None:
    data = await _prepared_room(api_client)
    request = _participant_request(data["settlement"])

    assert data["settlement"]["payer_details_configured"] is True
    assert data["settlement"]["payee_vpa"] == "receiptsplit.test@upi"
    assert request["amount_paise"] == 500
    assert request["status"] == "due"
    assert request["payment_reference"].startswith("RS-")
    assert "creator_token" not in request
    assert "participant_token" not in request


async def test_participant_opens_claims_and_creator_confirms_payment(api_client: Any) -> None:
    data = await _prepared_room(api_client)
    room_id = data["room"]["id"]
    request_id = _participant_request(data["settlement"])["id"]

    opened = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/open-payment",
        headers=bearer(data["participant_token"]),
    )
    assert opened.status_code == 200
    opened_body = opened.json()
    assert opened_body["status"] == "payment_opened"
    assert opened_body["amount_paise"] == 500
    assert "am=5.00" in opened_body["upi_uri"]
    assert "ReceiptSplit does not verify bank transfer." in opened_body["disclaimer"]

    claimed = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/claim-paid",
        headers=bearer(data["participant_token"]),
    )
    assert claimed.status_code == 200
    assert claimed.json()["status"] == "claimed_paid"

    confirmed = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/confirm",
        headers=bearer(data["creator_token"]),
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "payer_confirmed"


async def test_creator_can_dispute_and_participant_can_reopen(api_client: Any) -> None:
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
        json={"reason": "Could not match payment"},
        headers=bearer(data["creator_token"]),
    )
    assert disputed.status_code == 200
    assert disputed.json()["status"] == "disputed"

    reopened = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/open-payment",
        headers=bearer(data["participant_token"]),
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "payment_opened"


async def test_participant_cannot_prepare_confirm_or_dispute(api_client: Any) -> None:
    data = await _prepared_room(api_client)
    room_id = data["room"]["id"]
    request_id = _participant_request(data["settlement"])["id"]
    participant_headers = bearer(data["participant_token"])

    prepare = await api_client.post(
        f"/api/rooms/{room_id}/settlement/prepare",
        headers=participant_headers,
    )
    confirm = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/confirm",
        headers=participant_headers,
    )
    dispute = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/dispute",
        json={"reason": "no"},
        headers=participant_headers,
    )

    assert prepare.status_code == 403
    assert confirm.status_code == 403
    assert dispute.status_code == 403


async def test_cross_room_participant_cannot_open_request(api_client: Any) -> None:
    data = await _prepared_room(api_client)
    other_room = await _locked_room(api_client)
    room_id = data["room"]["id"]
    request_id = _participant_request(data["settlement"])["id"]

    response = await api_client.post(
        f"/api/rooms/{room_id}/settlement/requests/{request_id}/open-payment",
        headers=bearer(other_room["participant_token"]),
    )

    assert response.status_code == 403
