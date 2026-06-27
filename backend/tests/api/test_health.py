from typing import Any

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_check(api_client: Any) -> Any:
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
