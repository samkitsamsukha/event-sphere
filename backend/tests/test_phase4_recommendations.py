from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.user import User
from app.services import embeddings
from app.services.embeddings import generate_user_profile_embedding
from app.services.recommendations import cosine_similarity, time_decay


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


async def user(client: AsyncClient, role: str = "CUSTOMER") -> tuple[str, dict[str, str]]:
    email = f"{role.lower()}-{uuid4()}@example.com"
    response = await client.post(
        "/api/auth/register",
        json={"name": "Recommendation User", "email": email, "password": "password123", "role": role},
    )
    assert response.status_code == 201
    return email, {"Authorization": f"Bearer {response.json()['access_token']}"}


async def cleanup(*emails: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email.in_(emails)))
        await db.commit()
    await engine.dispose()


def payload(title: str, category: str = "Technology") -> dict[str, object]:
    return {
        "title": title,
        "description": "A useful event",
        "category": category,
        "tags": ["python"],
        "start_time": (datetime.now(UTC) + timedelta(days=4)).isoformat(),
        "end_time": (datetime.now(UTC) + timedelta(days=4, hours=1)).isoformat(),
    }


def test_embedding_profile_and_similarity_are_deterministic() -> None:
    profile = generate_user_profile_embedding([[1.0, 0.0], [0.0, 1.0]], [8.0, 1.0])
    assert profile is not None
    assert profile[0] > profile[1]
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert time_decay(0) == pytest.approx(1.0)
    assert time_decay(10) < time_decay(1)


def test_event_embedding_service_validates_model_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings, "embed_text", lambda _: [0.25] * 384)
    assert len(embeddings.generate_event_embedding("event text")) == 384
    monkeypatch.setattr(embeddings, "embed_text", lambda _: [0.25])
    with pytest.raises(ValueError, match="384"):
        embeddings.generate_event_embedding("event text")


@pytest.mark.asyncio
async def test_interaction_api_validates_and_deduplicates(client: AsyncClient) -> None:
    email, headers = await user(client)
    publisher_email, publisher_headers = await user(client, "PUBLISHER")
    try:
        event = await client.post("/api/events", headers=publisher_headers, json=payload("Tracked"))
        event_id = event.json()["id"]
        recorded = await client.post(
            "/api/interactions",
            headers=headers,
            json={"event_id": event_id, "interaction_type": "VIEW", "metadata": {"source": "home"}},
        )
        assert recorded.status_code == 201
        assert recorded.json()["metadata"] == {"source": "home"}
        duplicate = await client.post(
            "/api/interactions",
            headers=headers,
            json={"event_id": event_id, "interaction_type": "VIEW"},
        )
        assert duplicate.status_code == 409
        history = await client.get("/api/interactions/me", headers=headers)
        assert len(history.json()) == 1
    finally:
        await cleanup(email, publisher_email)


@pytest.mark.asyncio
async def test_recommendations_filter_registered_and_use_interests(client: AsyncClient) -> None:
    email, headers = await user(client)
    publisher_email, publisher_headers = await user(client, "PUBLISHER")
    try:
        interest_name = f"Technology-{uuid4().hex[:8]}"
        first = await client.post(
            "/api/events",
            headers=publisher_headers,
            json=payload("Technology Workshop", interest_name),
        )
        second = await client.post(
            "/api/events", headers=publisher_headers, json=payload("Other Workshop", "Design")
        )
        for response in (first, second):
            await client.post(f"/api/events/{response.json()['id']}/publish", headers=publisher_headers)

        interests = await client.post(
            "/api/users/me/interests",
            headers=headers,
            json={"name": interest_name, "category": interest_name},
        )
        assert interests.status_code == 201
        registered = await client.post(
            "/api/interactions",
            headers=headers,
            json={"event_id": first.json()["id"], "interaction_type": "REGISTER"},
        )
        assert registered.status_code == 201
        recommendations = await client.get("/api/recommendations", headers=headers)
        assert recommendations.status_code == 200
        assert all(item["id"] != first.json()["id"] for item in recommendations.json())
        debug = await client.get("/api/recommendations/debug", headers=headers)
        assert debug.status_code == 200
        assert {"event_id", "final_score"}.issubset(debug.json()[0])
    finally:
        await cleanup(email, publisher_email)


@pytest.mark.asyncio
async def test_no_eligible_events_returns_empty(client: AsyncClient) -> None:
    email, headers = await user(client)
    try:
        response = await client.get("/api/recommendations", headers=headers)
        assert response.status_code == 200
        assert response.json() == []
    finally:
        await cleanup(email)
