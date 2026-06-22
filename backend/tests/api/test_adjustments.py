import pytest
from typing import Any

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
