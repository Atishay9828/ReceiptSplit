from typing import Any

import pytest
from sqlalchemy import text

from tests.api.conftest import bearer

pytestmark = pytest.mark.asyncio


async def test_add_adjustment(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/adjustments",
        json={
            "type": "tax",
            "label": "GST",
            "amount_paise": 1800,
            "allocation_method": "equal",
        },
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 201
    assert response.json()["label"] == "GST"


async def test_add_adjustment_sanitizes_html_and_null_bytes(api_client: Any, db_session: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()

    response = await api_client.post(
        f"/api/rooms/{created['room']['id']}/adjustments",
        json={
            "type": "tax",
            "label": "<script>alert('xss')</script>GST\x00",
            "amount_paise": 1800,
            "allocation_method": "equal",
        },
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 201
    adjustment = response.json()
    assert adjustment["label"] == "alert('xss')GST"

    stored = await db_session.execute(
        text("SELECT label FROM split_adjustments WHERE id = :id"),
        {"id": adjustment["id"]},
    )
    persisted_label = stored.scalar_one()
    assert persisted_label == "alert('xss')GST"
    assert "<script" not in persisted_label
    assert "\x00" not in persisted_label


async def test_update_adjustment(api_client: Any) -> Any:
    created = (await api_client.post("/api/rooms", json={"split_mode": "equal"})).json()
    adjustment = (
        await api_client.post(
            f"/api/rooms/{created['room']['id']}/adjustments",
            json={"type": "tax", "label": "GST", "amount_paise": 1800},
            headers=bearer(created["creator_token"]),
        )
    ).json()

    response = await api_client.patch(
        f"/api/rooms/{created['room']['id']}/adjustments/{adjustment['id']}",
        json={"version": adjustment["version"], "label": "CGST + SGST"},
        headers=bearer(created["creator_token"]),
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
