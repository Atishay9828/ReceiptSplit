import pytest
from typing import Any

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
