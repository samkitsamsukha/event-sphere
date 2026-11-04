import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_does_not_expose_configuration() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "secret" not in response.text.lower()


@pytest.mark.asyncio
async def test_validation_errors_use_consistent_envelope() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == 422
