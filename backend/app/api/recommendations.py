from typing import Annotated
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc

from app.api.deps import DbSession, get_current_user
from app.core.config import settings
from app.models.event import Event, EventStatus
from app.models.search_history import SearchHistory
from app.models.user import User
from app.schemas.recommendation import RecommendationDebug, RecommendationResponse
from app.services.embeddings import embed_text
from app.services.recommendations import RecommendationService, cosine_similarity, invalidate_profile_cache
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class SearchHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    query: str
    created_at: datetime


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


@router.get("/search/history", response_model=list[SearchHistoryResponse])
async def search_history(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=8, ge=1, le=20),
) -> list[SearchHistoryResponse]:
    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
        .order_by(desc(SearchHistory.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/search", response_model=list[RecommendationResponse])
async def semantic_search(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    q: str = Query(min_length=2, max_length=500),
    limit: int = Query(default=12, ge=1, le=50),
) -> list[Event]:
    clean_query = q.strip()
    query_vector = embed_text(clean_query)

    future_events = (
        select(Event)
        .where(
            Event.status == EventStatus.PUBLISHED,
            Event.start_time > datetime.now(UTC),
        )
        .limit(200)
    )
    result = await db.execute(future_events)
    events = list(result.scalars().all())
    if not events:
        history = SearchHistory(user_id=current_user.id, query=clean_query, embedding=query_vector)
        db.add(history)
        await db.commit()
        invalidate_profile_cache(current_user.id)
        return []

    terms = {term for term in clean_query.casefold().replace("-", " ").split() if len(term) > 2}
    ranked: list[tuple[float, Event]] = []
    for event in events:
        semantic_score = 0.0
        if event.embedding is not None:
            try:
                semantic_score = max(
                    0.0,
                    min(1.0, (cosine_similarity(query_vector, list(event.embedding)) + 1.0) / 2.0),
                )
            except ValueError:
                semantic_score = 0.0

        searchable = " ".join(
            [
                event.title or "",
                event.description or "",
                event.category or "",
                event.location or "",
                " ".join(event.tags or []),
                event.semantic_text or "",
            ]
        ).casefold()
        text_hits = sum(1 for term in terms if term in searchable)
        text_score = text_hits / len(terms) if terms else 0.0
        final_score = 0.78 * semantic_score + 0.22 * text_score
        ranked.append((final_score, event))

    ranked.sort(key=lambda item: (-item[0], item[1].start_time))

    history = SearchHistory(user_id=current_user.id, query=clean_query, embedding=query_vector)
    db.add(history)
    await db.commit()
    invalidate_profile_cache(current_user.id)
    return [event for _, event in ranked[:limit]]
