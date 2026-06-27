from typing import Any

import pytest
from sqlalchemy import text

from app.shared.types import COLOR_PALETTE

pytestmark = pytest.mark.asyncio


async def test_join_room_valid_color(api_client: Any) -> Any:
    room_resp = await api_client.post("/api/rooms", json={"split_mode": "equal"})
    assert room_resp.status_code == 201
    room = room_resp.json()

    join_resp = await api_client.post(
        f"/api/rooms/{room['room']['id']}/join",
        json={
            "invite_token": room["invite_token"],
            "nickname": "Alice",
            "color": COLOR_PALETTE[1],
        },
    )
    assert join_resp.status_code == 201
    assert join_resp.json()["participant"]["color"] == COLOR_PALETTE[1]


async def test_join_room_no_color_assigns_from_palette(api_client: Any) -> Any:
    room_resp = await api_client.post("/api/rooms", json={"split_mode": "equal"})
    room = room_resp.json()

    join_resp = await api_client.post(
        f"/api/rooms/{room['room']['id']}/join",
        json={
            "invite_token": room["invite_token"],
            "nickname": "Bob",
        },
    )
    assert join_resp.status_code == 201
    assert join_resp.json()["participant"]["color"] in COLOR_PALETTE


async def test_join_room_invalid_hex_fails(api_client: Any) -> Any:
    room_resp = await api_client.post("/api/rooms", json={"split_mode": "equal"})
    room = room_resp.json()

    join_resp = await api_client.post(
        f"/api/rooms/{room['room']['id']}/join",
        json={
            "invite_token": room["invite_token"],
            "nickname": "Charlie",
            "color": "not_a_hex",
        },
    )
    assert join_resp.status_code == 400


async def test_join_room_arbitrary_hex_fails(api_client: Any) -> Any:
    room_resp = await api_client.post("/api/rooms", json={"split_mode": "equal"})
    room = room_resp.json()

    join_resp = await api_client.post(
        f"/api/rooms/{room['room']['id']}/join",
        json={
            "invite_token": room["invite_token"],
            "nickname": "Dave",
            "color": "#112233",  # valid hex, but not in COLOR_PALETTE
        },
    )
    assert join_resp.status_code == 400


async def test_join_room_nickname_sanitization(api_client: Any, db_session: Any) -> Any:
    room_resp = await api_client.post("/api/rooms", json={"split_mode": "equal"})
    room = room_resp.json()

    join_resp = await api_client.post(
        f"/api/rooms/{room['room']['id']}/join",
        json={
            "invite_token": room["invite_token"],
            "nickname": "<script>alert('xss')</script>Eve\x00",
        },
    )
    assert join_resp.status_code == 201
    participant = join_resp.json()["participant"]
    assert participant["nickname"] == "alert('xss')Eve"

    stored = await db_session.execute(
        text("SELECT nickname FROM room_participants WHERE id = :id"),
        {"id": participant["id"]},
    )
    persisted_nickname = stored.scalar_one()
    assert persisted_nickname == "alert('xss')Eve"
    assert "<script" not in persisted_nickname
    assert "\x00" not in persisted_nickname
