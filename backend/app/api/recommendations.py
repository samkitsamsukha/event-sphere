from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import DbSession, get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.recommendation import RecommendationDebug, RecommendationResponse
from app.services.recommendations import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationResponse])
async def get_recommendations(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=10, ge=1, le=50),
) -> list:
    results = await RecommendationService(db).recommend(current_user.id, limit)
    return [item.event for item in results]


@router.get("/debug", response_model=list[RecommendationDebug])
async def debug_recommendations(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=10, ge=1, le=50),
) -> list[RecommendationDebug]:
    if settings.environment.lower() not in {"development", "dev", "test"}:
        raise HTTPException(status_code=404, detail="Not found")
    results = await RecommendationService(db).recommend(current_user.id, limit)
    return [
        RecommendationDebug(
            event_id=item.event.id,
            semantic_score=item.semantic_score,
            interest_score=item.interest_score,
            behavior_score=item.behavior_score,
            popularity_score=item.popularity_score,
            recency_score=item.recency_score,
            final_score=item.final_score,
        )
        for item in results
    ]
