from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.event import EventStatus


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    publisher_id: int
    title: str
    description: str
    category: str | None
    tags: list[str]
    location: str | None
    start_time: datetime
    end_time: datetime
    capacity: int | None
    status: EventStatus


class RecommendationDebug(BaseModel):
    event_id: int
    semantic_score: float
    interest_score: float
    behavior_score: float
    popularity_score: float
    recency_score: float
    final_score: float
