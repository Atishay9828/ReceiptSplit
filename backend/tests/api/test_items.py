from typing import Any

import pytest
from sqlalchemy import text

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


async def _room(api_client: Any, split_mode: str = "equal") -> Any:
    return (await api_client.post("/api/rooms", json={"split_mode": split_mode})).json()


async def _activate(api_client: Any, created: dict[str, Any]) -> Any:
    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "status": "active"},
        headers=bearer(created["creator_token"]),
    )
    assert response.status_code == 200
    created["room"] = response.json()
    return created


async def test_add_item(api_client: Any) -> Any:
    created = await _room(api_client)

    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/items",
        json={"name": "Burger", "quantity": 2, "total_paise": 50000},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Burger"
    assert response.json()["quantity"] == 2


async def test_add_item_sanitizes_html_and_null_bytes(api_client: Any, db_session: Any) -> Any:
    created = await _room(api_client)

    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/items",
        json={
            "name": "<script>alert('xss')</script>Burger\x00",
            "quantity": 1,
            "total_paise": 25000,
        },
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 201
    item = response.json()
    assert item["name"] == "alert('xss')Burger"

    stored = await db_session.execute(
        text("SELECT name FROM line_items WHERE id = :id"),
        {"id": item["id"]},
    )
    persisted_name = stored.scalar_one()
    assert persisted_name == "alert('xss')Burger"
    assert "<script" not in persisted_name
    assert "\x00" not in persisted_name


async def test_update_item(api_client: Any) -> Any:
    created = await _room(api_client)
    item = (
        await api_client.post(
            f"/api/rooms/{created['room']['id']}/items",
            json={"name": "Burger", "quantity": 1, "total_paise": 25000},
            headers=bearer(created["creator_token"]),
        )
    ).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}/items/{item['id']}",
        json={"version": item["version"], "name": "Veg Burger"},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True


async def test_delete_item(api_client: Any) -> Any:
    created = await _room(api_client)
    item = (
        await api_client.post(
            f"/api/rooms/{created['room']['id']}/items",
            json={"name": "Burger", "quantity": 1, "total_paise": 25000},
            headers=bearer(created["creator_token"]),
        )
    ).json()

    response = await api_client.delete(
        f"/api/rooms/{created['room']['id']}/items/{item['id']}",
        params={"version": item["version"]},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True


async def test_claim_item(api_client: Any) -> Any:
    created = await _activate(api_client, await _room(api_client, split_mode="item_wise"))
    joined = (
        await api_client.post(
            f"/api/rooms/{created['room']['id']}/join",
            json={
                "invite_token": created["invite_token"],
                "nickname": "Bob",
            },
        )
    ).json()
    item = (
        await api_client.post(
            f"/api/rooms/{created['room']['id']}/items",
            json={"name": "Burger", "quantity": 1, "total_paise": 25000},
            headers=bearer(created["creator_token"]),
        )
    ).json()

    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/items/{item['id']}/claim",
        json={"item_version": item["version"], "claimed_qty": 1},
        headers=bearer(joined["participant_token"]),
    )

    assert response.status_code == 201
    assert response.json()["line_item_id"] == item["id"]
