from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import EventStatus


class EventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=2)
    location: str | None = None
    start_time: datetime
    end_time: datetime
    capacity: int | None = Field(default=None, gt=0)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    publisher_id: int
    title: str
    description: str
    location: str | None
    start_time: datetime
    end_time: datetime
    capacity: int | None
    status: EventStatus
