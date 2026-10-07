from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, asc, desc, or_, select

from app.api.deps import DbSession, require_publisher
from app.models.event import Event, EventStatus
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.services.event_semantics import update_event_semantic_text

router = APIRouter(prefix="/events", tags=["events"])


def validate_event_times(start_time: datetime, end_time: datetime) -> None:
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")


async def get_owned_event(event_id: int, user_id: int, db: DbSession) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.publisher_id != user_id:
        raise HTTPException(status_code=403, detail="You do not own this event")
    return event


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_publisher)],
) -> Event:
    validate_event_times(payload.start_time, payload.end_time)
    event = Event(
        **payload.model_dump(),
        publisher_id=current_user.id,
        status=EventStatus.DRAFT,
        semantic_text="",
    )
    update_event_semantic_text(event)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("", response_model=list[EventResponse])
async def list_events(
    db: DbSession,
    keyword: str | None = None,
    category: str | None = None,
    location: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="start_time", pattern="^(start_time|created_at|title)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> list[Event]:
    query: Select[tuple[Event]] = select(Event).where(Event.status == EventStatus.PUBLISHED)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(
            or_(
                Event.title.ilike(pattern),
                Event.description.ilike(pattern),
                Event.semantic_text.ilike(pattern),
            )
        )
    if category:
        query = query.where(Event.category.ilike(category.strip()))
    if location:
        query = query.where(Event.location.ilike(f"%{location.strip()}%"))
    if start_date:
        query = query.where(Event.start_time >= start_date)
    if end_date:
        query = query.where(Event.start_time <= end_date)

    sort_column = {
        "start_time": Event.start_time,
        "created_at": Event.created_at,
        "title": Event.title,
    }[sort_by]
    query = query.order_by((desc if sort_order == "desc" else asc)(sort_column))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/mine", response_model=list[EventResponse])
async def list_my_events(
    db: DbSession,
    current_user: Annotated[User, Depends(require_publisher)],
) -> list[Event]:
    result = await db.execute(
        select(Event).where(Event.publisher_id == current_user.id).order_by(Event.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: DbSession) -> Event:
    event = await db.get(Event, event_id)
    if event is None or event.status != EventStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    payload: EventUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_publisher)],
) -> Event:
    event = await get_owned_event(event_id, current_user.id, db)
    if event.status != EventStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft events can be updated")

    updates = payload.model_dump(exclude_unset=True)
    if "tags" in updates and updates["tags"] is None:
        raise HTTPException(status_code=422, detail="tags must be a list")
    start_time = updates.get("start_time", event.start_time)
    end_time = updates.get("end_time", event.end_time)
    validate_event_times(start_time, end_time)
    for field, value in updates.items():
        setattr(event, field, value)
    update_event_semantic_text(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(require_publisher)],
) -> Response:
    event = await get_owned_event(event_id, current_user.id, db)
    await db.delete(event)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{event_id}/publish", response_model=EventResponse)
async def publish_event(
    event_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(require_publisher)],
) -> Event:
    event = await get_owned_event(event_id, current_user.id, db)
    if event.status != EventStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft events can be published")
    event.status = EventStatus.PUBLISHED
    await db.commit()
    await db.refresh(event)
    return event


@router.post("/{event_id}/cancel", response_model=EventResponse)
async def cancel_event(
    event_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(require_publisher)],
) -> Event:
    event = await get_owned_event(event_id, current_user.id, db)
    if event.status != EventStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Only published events can be cancelled")
    event.status = EventStatus.CANCELLED
    await db.commit()
    await db.refresh(event)
    return event
