from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


def _dev_jwt(subject: str, email: str | None = None) -> str:
    header = {"alg": "none", "typ": "JWT"}
    payload: dict[str, str] = {"sub": subject}
    if email is not None:
        payload["email"] = email

    def encode(value: dict[str, str]) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{encode(header)}.{encode(payload)}.signature"


async def test_auth_me_with_valid_user_jwt(api_client: Any) -> None:
    response = await api_client.get(
        "/api/auth/me",
        headers=bearer(_dev_jwt("owner-subject", "owner@example.com")),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "dev"
    assert body["subject"] == "owner-subject"
    assert body["email"] == "owner@example.com"
    assert "token" not in body
    assert "token_hash" not in body


async def test_auth_me_rejects_participant_token(api_client: Any) -> None:
    room = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    joined = (
        await api_client.post(
            f"/api/rooms/{room['room']['id']}/join",
            json={"invite_token": room["invite_token"], "nickname": "Bob"},
        )
    ).json()

    response = await api_client.get(
        "/api/auth/me",
        headers=bearer(joined["participant_token"]),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_AUTHORIZED"


async def test_auth_me_rejects_invalid_jwt(api_client: Any) -> None:
    response = await api_client.get("/api/auth/me", headers=bearer("bad.jwt.token"))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_owner_jwt_can_create_and_admin_owned_room(api_client: Any) -> None:
    owner_token = _dev_jwt("owner-subject")
    created = (
        await api_client.post(
            "/api/rooms",
            json={"split_mode": "equal"},
            headers=bearer(owner_token),
        )
    ).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "payer_name": "AJ"},
        headers=bearer(owner_token),
    )

    assert response.status_code == 200
    assert response.json()["payer_name"] == "AJ"


async def test_unrelated_user_jwt_rejected_from_creator_route(api_client: Any) -> None:
    created = (
        await api_client.post(
            "/api/rooms",
            json={"split_mode": "equal"},
            headers=bearer(_dev_jwt("owner-subject")),
        )
    ).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "payer_name": "Mallory"},
        headers=bearer(_dev_jwt("unrelated-subject")),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_AUTHORIZED"


async def test_legacy_creator_token_still_works(api_client: Any) -> None:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "payer_name": "Legacy"},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["payer_name"] == "Legacy"


async def test_participant_token_rejected_from_creator_route(api_client: Any) -> None:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    joined = (
        await api_client.post(
            f"/api/rooms/{created['room']['id']}/join",
            json={"invite_token": created["invite_token"], "nickname": "Bob"},
        )
    ).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}",
        json={"version": created["room"]["version"], "payer_name": "Bob"},
        headers=bearer(joined["participant_token"]),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_AUTHORIZED"


async def test_cross_room_capability_token_rejected(api_client: Any) -> None:
    room_a = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    room_b = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.patch(
        f"/api/rooms/{room_b['room']['id']}",
        json={"version": room_b["room"]["version"], "payer_name": "Wrong Token"},
        headers=bearer(room_a["creator_token"]),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_create_room_without_user_jwt_preserves_legacy_behavior(api_client: Any) -> None:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    assert created["creator_token"].startswith("rs_cr_")
    assert created["invite_token"].startswith("rs_inv_")


async def test_user_rooms_lists_only_owned_rooms(api_client: Any) -> None:
    owner_token = _dev_jwt("owner-a")
    owned = (
        await api_client.post(
            "/api/rooms",
            json={"split_mode": "equal"},
            headers=bearer(owner_token),
        )
    ).json()
    await api_client.post(
        "/api/rooms",
        json={"split_mode": "equal"},
        headers=bearer(_dev_jwt("owner-b")),
    )

    response = await api_client.get("/api/users/me/rooms", headers=bearer(owner_token))

    assert response.status_code == 200
    assert [room["id"] for room in response.json()["rooms"]] == [owned["room"]["id"]]


async def test_no_token_hashes_in_responses(api_client: Any) -> None:
    response = await api_client.get("/api/auth/me", headers=bearer(_dev_jwt("owner-subject")))

    assert response.status_code == 200
    body = json.dumps(response.json())
    assert "token_hash" not in body
    assert "rs_cr_" not in body
    assert "rs_pt_" not in body
