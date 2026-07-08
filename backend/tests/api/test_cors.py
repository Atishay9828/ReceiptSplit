from fastapi.testclient import TestClient

from app.main import create_app


def test_cors_preflight_allows_settlement_payer_put() -> None:
    client = TestClient(create_app())

    response = client.options(
        "/api/rooms/00000000-0000-0000-0000-000000000000/settlement/payer",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "PUT" in response.headers["access-control-allow-methods"]
