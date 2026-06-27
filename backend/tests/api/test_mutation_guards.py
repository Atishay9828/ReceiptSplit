from typing import Any

import pytest

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


async def _room_to_settling(api_client: Any) -> Any:
    room_resp = await api_client.post("/api/rooms", json={"split_mode": "equal"})
    created = room_resp.json()

    # Need at least one item and one active participant (creator)
    await api_client.post(
        f"/api/rooms/{created['room']['id']}/items",
        json={"name": "Burger", "quantity": 1, "total_paise": 100},
        headers=bearer(created["creator_token"]),
    )

    # Active
    r1 = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": 1, "status": "active"},
        headers=bearer(created["creator_token"]),
    )

    # Settling
    r2 = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": r1.json()["version"], "status": "settling"},
        headers=bearer(created["creator_token"]),
    )

    created["room"] = r2.json()
    return created


async def test_cannot_add_item_when_settling(api_client: Any) -> Any:
    created = await _room_to_settling(api_client)

    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/items",
        json={"name": "Fries", "quantity": 1, "total_paise": 50},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 400  # InvalidStateTransition maps to 400
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


async def test_cannot_add_adjustment_when_settling(api_client: Any) -> Any:
    created = await _room_to_settling(api_client)

    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/adjustments",
        json={
            "type": "tax",
            "label": "GST",
            "amount_paise": 10,
            "allocation_method": "equal",
        },
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
