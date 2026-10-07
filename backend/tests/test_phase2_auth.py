from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.user import User


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client


@pytest.fixture
async def email() -> AsyncIterator[str]:
    value = f"test-{uuid4()}@example.com"
    yield value
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == value))
        await db.commit()
    await engine.dispose()


async def register(client: AsyncClient, email: str, role: str = "CUSTOMER") -> dict:
    response = await client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": "password123", "role": role},
    )
    assert response.status_code == 201
    return response.json()


async def auth_headers(client: AsyncClient, email: str, role: str = "CUSTOMER") -> dict[str, str]:
    token = (await register(client, email, role))["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_successful_registration(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": "password123"},
    )
    assert response.status_code == 201
    assert response.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_duplicate_email(client: AsyncClient, email: str) -> None:
    await register(client, email)
    response = await client.post(
        "/api/auth/register",
        json={"name": "Other User", "email": email, "password": "password123"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_successful_login(client: AsyncClient, email: str) -> None:
    await register(client, email)
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_invalid_password(client: AsyncClient, email: str) -> None:
    await register(client, email)
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client: AsyncClient, email: str) -> None:
    headers = await auth_headers(client, email)
    response = await client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert "password_hash" not in response.json()


@pytest.mark.asyncio
async def test_profile_retrieval(client: AsyncClient, email: str) -> None:
    headers = await auth_headers(client, email)
    response = await client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_updating_profile(client: AsyncClient, email: str) -> None:
    headers = await auth_headers(client, email)
    response = await client.put(
        "/api/users/me", headers=headers, json={"name": "Updated Name"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_adding_and_removing_interests(client: AsyncClient, email: str) -> None:
    headers = await auth_headers(client, email)
    added = await client.post(
        "/api/users/me/interests",
        headers=headers,
        json={"name": f"Music-{uuid4()}", "category": "Arts"},
    )
    assert added.status_code == 201
    interest_id = added.json()["id"]
    duplicate = await client.post(
        "/api/users/me/interests", headers=headers, json={"interest_id": interest_id}
    )
    assert duplicate.status_code == 409
    removed = await client.delete(
        f"/api/users/me/interests/{interest_id}", headers=headers
    )
    assert removed.status_code == 204


@pytest.mark.asyncio
async def test_publisher_customer_authorization(client: AsyncClient) -> None:
    customer_email = f"customer-{uuid4()}@example.com"
    publisher_email = f"publisher-{uuid4()}@example.com"
    try:
        customer_headers = await auth_headers(client, customer_email)
        publisher_headers = await auth_headers(client, publisher_email, "PUBLISHER")
        event = {
            "title": "Test Event",
            "description": "A test event",
            "start_time": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "end_time": (datetime.now(UTC) + timedelta(days=1, hours=1)).isoformat(),
        }
        customer_response = await client.post(
            "/api/events", headers=customer_headers, json=event
        )
        publisher_response = await client.post(
            "/api/events", headers=publisher_headers, json=event
        )
        assert customer_response.status_code == 403
        assert publisher_response.status_code == 201
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(User).where(User.email.in_([customer_email, publisher_email])))
            await db.commit()
        await engine.dispose()
