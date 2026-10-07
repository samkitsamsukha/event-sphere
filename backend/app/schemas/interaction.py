from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.interaction import InteractionType


class InteractionCreate(BaseModel):
    event_id: int = Field(gt=0)
    interaction_type: InteractionType
    metadata: dict | None = None


class InteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user_id: int
    event_id: int
    interaction_type: InteractionType
    metadata: dict | None = Field(default=None, validation_alias="metadata_")
    created_at: datetime
