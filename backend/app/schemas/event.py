from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.event import EventStatus


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str | None = None
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=20)
    start_time: datetime
    end_time: datetime
    capacity: int | None = Field(default=None, gt=0)

    @field_validator("title", "description")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = None
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = Field(default=None, max_length=20)
    start_time: datetime | None = None
    end_time: datetime | None = None
    capacity: int | None = Field(default=None, gt=0)

    @field_validator("title", "description")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    publisher_id: int
    title: str
    description: str
    location: str | None
    category: str | None
    tags: list[str]
    start_time: datetime
    end_time: datetime
    capacity: int | None
    status: EventStatus
    semantic_text: str
    created_at: datetime
    updated_at: datetime
