from typing import Any

import pytest

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


async def test_cross_room_token_rejected(api_client: Any) -> Any:
    room_a = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    room_b = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.get(
        f"/api/rooms/{room_b['room']['id']}",
        headers=bearer(room_a["creator_token"]),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_creator_required(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    joined = (
        await api_client.post(
            f"/api/rooms/{created['room']['id']}/join",
            json={
                "invite_token": created["invite_token"],
                "nickname": "Bob",
            },
        )
    ).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "payer_name": "Bob"},
        headers=bearer(joined["participant_token"]),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_AUTHORIZED"
