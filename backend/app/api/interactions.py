from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.models.event import Event
from app.models.interaction import Interaction
from app.models.user import User
from app.schemas.interaction import InteractionCreate, InteractionResponse

router = APIRouter(prefix="/interactions", tags=["interactions"])
_DEDUPLICATED_TYPES = {"VIEW", "CLICK", "SEARCH"}


@router.post("", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
async def create_interaction(
    payload: InteractionCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Interaction:
    event = await db.get(Event, payload.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if payload.interaction_type.value in _DEDUPLICATED_TYPES:
        cutoff = datetime.now(UTC) - timedelta(minutes=5)
        recent = await db.execute(
            select(Interaction).where(
                Interaction.user_id == current_user.id,
                Interaction.event_id == payload.event_id,
                Interaction.interaction_type == payload.interaction_type,
                Interaction.created_at >= cutoff,
            )
        )
        if recent.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Duplicate interaction recently recorded")

    interaction = Interaction(
        user_id=current_user.id,
        event_id=payload.event_id,
        interaction_type=payload.interaction_type,
        metadata_=payload.metadata,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return interaction


@router.get("/me", response_model=list[InteractionResponse])
async def list_my_interactions(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Interaction]:
    result = await db.execute(
        select(Interaction)
        .where(Interaction.user_id == current_user.id)
        .order_by(Interaction.created_at.desc())
    )
    return list(result.scalars().all())
