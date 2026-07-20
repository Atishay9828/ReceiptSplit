from typing import Any

import pytest

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


async def _settlement_room(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    room = (
        await api_client.patch(
            f"/api/rooms/{created['room']['id']}",
            json={"version": created["room"]["version"], "status": "active"},
            headers=bearer(created["creator_token"]),
        )
    ).json()
    created["room"] = room
    join_response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/join",
        json={
            "invite_token": created["invite_token"],
            "nickname": "Bob",
        },
    )
    assert join_response.status_code == 201
    item_response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/items",
        json={"name": "Burger", "quantity": 1, "total_paise": 1000},
        headers=bearer(created["creator_token"]),
    )
    assert item_response.status_code == 201
    return created


async def test_split_preview(api_client: Any) -> Any:
    created = await _settlement_room(api_client)

    response = await api_client.get(
        f"/api/rooms/{created['room']['id']}/split/preview",
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["grand_total_paise"] == 1000
    assert len(response.json()["participant_totals"]) == 2


async def test_split_preview_positive_discount_payload_subtracts(api_client: Any) -> Any:
    created = await _settlement_room(api_client)
    adjustment = await api_client.post(
        f"/api/rooms/{created['room']['id']}/adjustments",
        json={
            "type": "discount",
            "label": "Coupon",
            "amount_paise": 100,
            "allocation_method": "proportional",
        },
        headers=bearer(created["creator_token"]),
    )
    assert adjustment.status_code == 201

    response = await api_client.get(
        f"/api/rooms/{created['room']['id']}/split/preview",
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["grand_total_paise"] == 900


async def test_split_preview_updated_discount_amount_stays_subtractive(api_client: Any) -> Any:
    created = await _settlement_room(api_client)
    headers = bearer(created["creator_token"])
    adjustment = (
        await api_client.post(
            f"/api/rooms/{created['room']['id']}/adjustments",
            json={
                "type": "discount",
                "label": "Coupon",
                "amount_paise": 100,
                "allocation_method": "proportional",
            },
            headers=headers,
        )
    ).json()

    update = await api_client.patch(
        f"/api/rooms/{created['room']['id']}/adjustments/{adjustment['id']}",
        json={"version": adjustment["version"], "amount_paise": 200},
        headers=headers,
    )
    assert update.status_code == 200

    response = await api_client.get(
        f"/api/rooms/{created['room']['id']}/split/preview",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["grand_total_paise"] == 800


async def test_split_preview_percentage_adjustments(api_client: Any) -> Any:
    created = await _settlement_room(api_client)
    headers = bearer(created["creator_token"])
    tax = await api_client.post(
        f"/api/rooms/{created['room']['id']}/adjustments",
        json={
            "type": "tax",
            "label": "GST",
            "amount_paise": 0,
            "rate_basis_points": 500,
            "allocation_method": "proportional",
        },
        headers=headers,
    )
    discount = await api_client.post(
        f"/api/rooms/{created['room']['id']}/adjustments",
        json={
            "type": "discount",
            "label": "Discount",
            "amount_paise": 0,
            "rate_basis_points": 1000,
            "allocation_method": "proportional",
        },
        headers=headers,
    )
    assert tax.status_code == 201
    assert discount.status_code == 201

    response = await api_client.get(
        f"/api/rooms/{created['room']['id']}/split/preview",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["grand_total_paise"] == 950


async def test_split_preview_etag(api_client: Any) -> Any:
    created = await _settlement_room(api_client)
    url = f"/api/rooms/{created['room']['id']}/split/preview"
    headers = bearer(created["creator_token"])

    first = await api_client.get(url, headers=headers)
    second = await api_client.get(
        url,
        headers={**headers, "If-None-Match": first.headers["etag"]},
    )

    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    assert second.status_code == 304
    assert second.content == b""


async def test_split_lock(api_client: Any) -> Any:
    created = await _settlement_room(api_client)

    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/split/lock",
        json={"version": created["room"]["version"]},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 201
    assert response.json()["grand_total_paise"] == 1000


async def test_split_unlock(api_client: Any) -> Any:
    created = await _settlement_room(api_client)
    lock_response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/split/lock",
        json={"version": created["room"]["version"]},
        headers=bearer(created["creator_token"]),
    )
    assert lock_response.status_code == 201

    room = (
        await api_client.get(
            f"/api/rooms/{created['room']['id']}",
            headers=bearer(created["creator_token"]),
        )
    ).json()
    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/split/unlock",
        json={"version": room["version"]},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
