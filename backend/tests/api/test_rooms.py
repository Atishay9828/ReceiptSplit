from typing import Any

import pytest

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


async def test_create_room(api_client: Any) -> Any:
    response = await api_client.post("/api/rooms", json={"split_mode": "equal"})

    assert response.status_code == 201
    body = response.json()
    assert body["room"]["id"]
    assert body["room"]["status"] == "draft"
    assert body["room"]["split_mode"] == "equal"
    assert body["creator_token"]
    assert body["invite_token"]


async def test_get_room(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.get(
        f"/api/rooms/{created['room']['id']}",
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["room"]["id"]


async def test_get_room_summary(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "item_wise"})).json()
    room_id = created["room"]["id"]
    creator_headers = bearer(created["creator_token"])
    activated = await api_client.patch(
        f"/api/rooms/{room_id}",
        json={"version": created["room"]["version"], "status": "active"},
        headers=creator_headers,
    )
    assert activated.status_code == 200
    joined = (
        await api_client.post(
            f"/api/rooms/{room_id}/join",
            json={"invite_token": created["invite_token"], "nickname": "Bob"},
        )
    ).json()
    item = (
        await api_client.post(
            f"/api/rooms/{room_id}/items",
            json={"name": "Burger", "quantity": 2, "total_paise": 50000},
            headers=creator_headers,
        )
    ).json()
    adjustment = (
        await api_client.post(
            f"/api/rooms/{room_id}/adjustments",
            json={
                "type": "tax",
                "label": "GST",
                "amount_paise": 2500,
                "allocation_method": "equal",
            },
            headers=creator_headers,
        )
    ).json()
    claim = (
        await api_client.post(
            f"/api/rooms/{room_id}/items/{item['id']}/claim",
            json={"item_version": item["version"], "claimed_qty": 1},
            headers=bearer(joined["participant_token"]),
        )
    ).json()

    response = await api_client.get(
        f"/api/rooms/{room_id}/summary",
        headers=creator_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["room"]["id"] == room_id
    assert [participant["nickname"] for participant in body["participants"]] == [
        "Creator",
        "Bob",
    ]
    assert body["items"][0]["id"] == item["id"]
    assert body["items"][0]["name"] == "Burger"
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["total_paise"] == 50000
    assert body["adjustments"] == [adjustment]
    assert body["assignments"] == [claim]


async def test_update_room(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "payer_vpa": "aj@upi"},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["payer_vpa"] == "aj@upi"
    assert response.json()["version"] == created["room"]["version"] + 1


async def test_room_version_conflict(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    headers = bearer(created["creator_token"])
    url = f"/api/rooms/{created['room']['id']}"
    payload = {"version": created["room"]["version"], "payer_name": "AJ"}

    first = await api_client.patch(url, json=payload, headers=headers)
    second = await api_client.patch(url, json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "VERSION_CONFLICT"


async def test_update_room_mixed_payload(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "status": "active", "payer_vpa": "a@upi"},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 400
    assert "Cannot mix" in response.json()["detail"]


async def test_update_room_invalid_status_set(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "status": "settled"},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 400
    assert "cannot be set manually" in response.json()["detail"]
