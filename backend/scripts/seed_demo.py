"""Create deterministic demo accounts and published events for local development."""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.services.event_semantics import update_event_semantic_text

ADMIN_EMAIL = "admin@eventsphere.example.com"
ADMIN_PASSWORD = "Admin12345!"
DEMO_EMAIL = "demo@eventsphere.example.com"
DEMO_PASSWORD = "Demo12345!"
PUBLISHER_EMAIL = "publisher@eventsphere.example.com"
PUBLISHER_PASSWORD = "Publisher12345!"


async def get_or_create_user(
    session, name: str, email: str, password: str, role: UserRole
) -> User:
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )
        session.add(user)
        await session.flush()
    else:
        user.name = name
        user.role = role
        user.password_hash = hash_password(password)
    return user


async def main() -> None:
    events = [
        ("Future Forum", "Technology", "A bold conversation about humane technology and the future of work.", "The Foundry"),
        ("Night Market Sessions", "Music", "Live sets, local makers, and street food under the city lights.", "Riverside Warehouse"),
        ("Designing Tomorrow", "Design", "A practical, high-energy workshop for creators shaping what comes next.", "Studio 09"),
        ("Open Source Breakfast", "Technology", "Meet maintainers, swap ideas, and build useful things together.", "Common Ground Cafe"),
        ("The Creative Reset", "Education", "A focused half-day of prompts, people, and fresh perspective.", "The Atrium"),
        ("Community Run Club", "Community", "An easy-paced social run followed by coffee and good conversation.", "Central Park"),
    ]
    async with AsyncSessionLocal() as session:
        await get_or_create_user(session, "EventSphere Admin", ADMIN_EMAIL, ADMIN_PASSWORD, UserRole.ADMIN)
        await get_or_create_user(session, "Demo Explorer", DEMO_EMAIL, DEMO_PASSWORD, UserRole.CUSTOMER)
        publisher = await get_or_create_user(
            session, "Demo Publisher", PUBLISHER_EMAIL, PUBLISHER_PASSWORD, UserRole.PUBLISHER
        )
        await session.flush()
        for index, (title, category, description, location) in enumerate(events):
            existing = (
                await session.execute(select(Event).where(Event.title == title))
            ).scalar_one_or_none()
            start = datetime(2027, 1 + index, 10 + index, 18, 30, tzinfo=UTC)
            end = start.replace(hour=21, minute=0)
            if existing is None:
                existing = Event(
                    publisher_id=publisher.id,
                    title=title,
                    description=description,
                    category=category,
                    tags=[category.lower(), "featured", "community"],
                    location=location,
                    start_time=start,
                    end_time=end,
                    capacity=120,
                    status=EventStatus.PUBLISHED,
                    semantic_text="",
                )
                session.add(existing)
            else:
                existing.publisher_id = publisher.id
                existing.description = description
                existing.category = category
                existing.tags = [category.lower(), "featured", "community"]
                existing.location = location
                existing.start_time = start
                existing.end_time = end
                existing.capacity = 120
                existing.status = EventStatus.PUBLISHED
            update_event_semantic_text(existing)
        await session.commit()
    print(f"Seeded admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"Seeded demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"Seeded publisher: {PUBLISHER_EMAIL} / {PUBLISHER_PASSWORD}")
    print(f"Seeded {len(events)} published events.")


if __name__ == "__main__":
    asyncio.run(main())
