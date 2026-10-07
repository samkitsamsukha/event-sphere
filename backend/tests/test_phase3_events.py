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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


async def create_user(client: AsyncClient, role: str) -> tuple[str, dict[str, str]]:
    email = f"{role.lower()}-{uuid4()}@example.com"
    response = await client.post(
        "/api/auth/register",
        json={"name": f"{role} User", "email": email, "password": "password123", "role": role},
    )
    assert response.status_code == 201
    return email, {"Authorization": f"Bearer {response.json()['access_token']}"}


async def cleanup(*emails: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email.in_(emails)))
        await db.commit()
    await engine.dispose()


def event_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Python Workshop",
        "description": "Learn async Python",
        "location": "Kathmandu",
        "category": "Technology",
        "tags": ["python", "backend"],
        "start_time": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "end_time": (datetime.now(UTC) + timedelta(days=2, hours=2)).isoformat(),
        "capacity": 25,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_publisher_creates_draft_and_semantic_text(client: AsyncClient) -> None:
    email, headers = await create_user(client, "PUBLISHER")
    try:
        response = await client.post("/api/events", headers=headers, json=event_payload())
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "DRAFT"
        assert "Python Workshop" in body["semantic_text"]
        assert body["tags"] == ["python", "backend"]
    finally:
        await cleanup(email)


@pytest.mark.asyncio
async def test_customer_cannot_create_event(client: AsyncClient) -> None:
    email, headers = await create_user(client, "CUSTOMER")
    try:
        response = await client.post("/api/events", headers=headers, json=event_payload())
        assert response.status_code == 403
    finally:
        await cleanup(email)


@pytest.mark.asyncio
async def test_publisher_updates_own_event(client: AsyncClient) -> None:
    email, headers = await create_user(client, "PUBLISHER")
    try:
        created = await client.post("/api/events", headers=headers, json=event_payload())
        response = await client.put(
            f"/api/events/{created.json()['id']}",
            headers=headers,
            json={"title": "Updated Workshop", "category": "Education"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Workshop"
        assert "Updated Workshop" in response.json()["semantic_text"]
    finally:
        await cleanup(email)


@pytest.mark.asyncio
async def test_publisher_cannot_update_another_publishers_event(client: AsyncClient) -> None:
    owner_email, owner_headers = await create_user(client, "PUBLISHER")
    other_email, other_headers = await create_user(client, "PUBLISHER")
    try:
        created = await client.post("/api/events", headers=owner_headers, json=event_payload())
        response = await client.put(
            f"/api/events/{created.json()['id']}",
            headers=other_headers,
            json={"title": "Not Allowed"},
        )
        assert response.status_code == 403
    finally:
        await cleanup(owner_email, other_email)


@pytest.mark.asyncio
async def test_publish_and_cancel_lifecycle(client: AsyncClient) -> None:
    email, headers = await create_user(client, "PUBLISHER")
    try:
        created = await client.post("/api/events", headers=headers, json=event_payload())
        event_id = created.json()["id"]
        published = await client.post(f"/api/events/{event_id}/publish", headers=headers)
        assert published.status_code == 200
        assert published.json()["status"] == "PUBLISHED"
        cancelled = await client.post(f"/api/events/{event_id}/cancel", headers=headers)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"
        invalid = await client.post(f"/api/events/{event_id}/publish", headers=headers)
        assert invalid.status_code == 400
    finally:
        await cleanup(email)


@pytest.mark.asyncio
async def test_invalid_dates_are_rejected(client: AsyncClient) -> None:
    email, headers = await create_user(client, "PUBLISHER")
    try:
        response = await client.post(
            "/api/events",
            headers=headers,
            json=event_payload(
                start_time=(datetime.now(UTC) + timedelta(days=2)).isoformat(),
                end_time=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
            ),
        )
        assert response.status_code == 400
    finally:
        await cleanup(email)


@pytest.mark.asyncio
async def test_listing_filtering_pagination_and_details(client: AsyncClient) -> None:
    email, headers = await create_user(client, "PUBLISHER")
    try:
        first = await client.post(
            "/api/events",
            headers=headers,
            json=event_payload(title="Python Meetup", location="Lalitpur"),
        )
        second = await client.post(
            "/api/events",
            headers=headers,
            json=event_payload(title="Design Meetup", category="Design"),
        )
        await client.post(f"/api/events/{first.json()['id']}/publish", headers=headers)
        await client.post(f"/api/events/{second.json()['id']}/publish", headers=headers)

        listing = await client.get("/api/events", params={"keyword": "Python", "page_size": 1})
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        assert listing.json()[0]["title"] == "Python Meetup"

        filtered = await client.get("/api/events", params={"category": "Design"})
        assert len(filtered.json()) == 1
        assert filtered.json()[0]["title"] == "Design Meetup"

        paged = await client.get("/api/events", params={"page": 2, "page_size": 1})
        assert len(paged.json()) == 1

        details = await client.get(f"/api/events/{first.json()['id']}")
        assert details.status_code == 200
        assert details.json()["location"] == "Lalitpur"
    finally:
        await cleanup(email)
