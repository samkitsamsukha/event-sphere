from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.schemas.event import EventCreate, EventResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.PUBLISHER:
        raise HTTPException(status_code=403, detail="Publisher role required")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    event = Event(
        **payload.model_dump(),
        publisher_id=current_user.id,
        status=EventStatus.PUBLISHED,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("", response_model=list[EventResponse])
async def list_events(db: DbSession):
    result = await db.execute(
        select(Event)
        .where(Event.status == EventStatus.PUBLISHED)
        .order_by(Event.start_time)
    )
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: DbSession):
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
