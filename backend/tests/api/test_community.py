from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


def dev_jwt(subject: str, email: str) -> str:
    def encode(value: dict[str, str]) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode({'sub': subject, 'email': email})}.signature"


async def set_profile(api_client: Any, token: str, username: str, display_name: str) -> None:
    response = await api_client.put(
        "/api/users/me/profile",
        headers=bearer(token),
        json={"username": username, "display_name": display_name},
    )
    assert response.status_code == 200


async def test_accounts_friends_persistent_rooms_and_member_access(api_client: Any) -> None:
    owner_token = dev_jwt("owner", "owner@example.com")
    friend_token = dev_jwt("friend", "friend@example.com")
    await set_profile(api_client, owner_token, "aj", "AJ")
    await set_profile(api_client, friend_token, "sam", "Sam")

    friend = await api_client.post(
        "/api/users/me/friends",
        headers=bearer(owner_token),
        json={"username": "sam"},
    )
    assert friend.status_code == 201
    assert friend.json()["username"] == "sam"
    assert "email" not in friend.json()

    group = await api_client.post(
        "/api/groups",
        headers=bearer(owner_token),
        json={"name": "Goa trip", "member_usernames": ["sam"]},
    )
    assert group.status_code == 201
    group_id = group.json()["id"]
    assert [member["username"] for member in group.json()["members"]] == ["aj", "sam"]
    assert all("email" not in member for member in group.json()["members"])

    created = await api_client.post(
        f"/api/groups/{group_id}/bills",
        headers=bearer(owner_token),
        json={"title": "Dinner day 1", "split_mode": "item_wise"},
    )
    assert created.status_code == 201
    room = created.json()["bill"]["room"]
    assert room["title"] == "Dinner day 1"
    assert room["group_id"] == group_id

    activated = await api_client.patch(
        f"/api/rooms/{room['id']}",
        headers=bearer(owner_token),
        json={"version": room["version"], "status": "active"},
    )
    assert activated.status_code == 200
    item = await api_client.post(
        f"/api/rooms/{room['id']}/items",
        headers=bearer(owner_token),
        json={
            "name": "Shared pizza",
            "quantity": 1,
            "total_paise": 1000,
            "allocation_mode": "equal",
        },
    )
    assert item.status_code == 201
    active_groups = await api_client.get("/api/groups", headers=bearer(owner_token))
    assert active_groups.status_code == 200
    active_group = active_groups.json()["groups"][0]
    assert active_group["bills"][0]["grand_total_paise"] == 1000
    assert active_group["total_paise"] == 1000
    assert active_group["pending_paise"] == 0
    assert active_group["cleared_paise"] == 0

    locked = await api_client.post(
        f"/api/rooms/{room['id']}/split/lock",
        headers=bearer(owner_token),
        json={"version": activated.json()["version"]},
    )
    assert locked.status_code == 201

    owner_groups = await api_client.get("/api/groups", headers=bearer(owner_token))
    friend_groups = await api_client.get("/api/groups", headers=bearer(friend_token))
    assert owner_groups.status_code == 200
    assert friend_groups.status_code == 200
    assert owner_groups.json()["groups"][0]["bills"][0]["title"] == "Dinner day 1"
    assert owner_groups.json()["groups"][0]["pending_paise"] == 500
    assert owner_groups.json()["groups"][0]["cleared_paise"] == 0
    assert friend_groups.json()["groups"][0]["bills"][0]["current_participant_id"]

    summary = await api_client.get(
        f"/api/rooms/{room['id']}/summary", headers=bearer(friend_token)
    )
    assert summary.status_code == 200
    assert any(participant["user_id"] for participant in summary.json()["participants"])

    payer = await api_client.put(
        f"/api/rooms/{room['id']}/settlement/payer",
        headers=bearer(owner_token),
        json={"payee_vpa": "aj@upi", "payee_name": "AJ"},
    )
    assert payer.status_code == 200
    prepared = await api_client.post(
        f"/api/rooms/{room['id']}/settlement/prepare",
        headers=bearer(owner_token),
    )
    assert prepared.status_code == 201
    request_id = prepared.json()["requests"][0]["id"]

    member_settlement = await api_client.get(
        f"/api/rooms/{room['id']}/settlement",
        headers=bearer(friend_token),
    )
    assert member_settlement.status_code == 200
    assert [entry["id"] for entry in member_settlement.json()["requests"]] == [request_id]

    claimed = await api_client.post(
        f"/api/rooms/{room['id']}/settlement/requests/{request_id}/claim-paid",
        headers=bearer(friend_token),
        json={"amount_paise": 200},
    )
    assert claimed.status_code == 200
    confirmed = await api_client.post(
        f"/api/rooms/{room['id']}/settlement/requests/{request_id}/confirm",
        headers=bearer(owner_token),
    )
    assert confirmed.status_code == 200

    partial_groups = await api_client.get("/api/groups", headers=bearer(owner_token))
    assert partial_groups.json()["groups"][0]["pending_paise"] == 300
    assert partial_groups.json()["groups"][0]["cleared_paise"] == 200

    remaining_claim = await api_client.post(
        f"/api/rooms/{room['id']}/settlement/requests/{request_id}/claim-paid",
        headers=bearer(friend_token),
    )
    assert remaining_claim.status_code == 200
    assert remaining_claim.json()["pending_claim_amount_paise"] == 300
    final_confirmation = await api_client.post(
        f"/api/rooms/{room['id']}/settlement/requests/{request_id}/confirm",
        headers=bearer(owner_token),
    )
    assert final_confirmation.status_code == 200

    cleared_groups = await api_client.get("/api/groups", headers=bearer(owner_token))
    assert cleared_groups.json()["groups"][0]["pending_paise"] == 0
    assert cleared_groups.json()["groups"][0]["cleared_paise"] == 500


async def test_profile_rejects_duplicate_username(api_client: Any) -> None:
    first = dev_jwt("first", "first@example.com")
    second = dev_jwt("second", "second@example.com")
    await set_profile(api_client, first, "taken_name", "First")

    response = await api_client.put(
        "/api/users/me/profile",
        headers=bearer(second),
        json={"username": "taken_name", "display_name": "Second"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USERNAME_TAKEN"
