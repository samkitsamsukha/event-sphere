import math
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.event import Event, EventStatus
from app.models.interaction import Interaction, InteractionType
from app.models.interest import Interest, UserInterest
from app.services.embeddings import generate_user_profile_embedding


@dataclass(frozen=True)
class RecommendationFeatures:
    event: Event
    semantic_score: float
    interest_score: float
    behavior_score: float
    popularity_score: float
    recency_score: float
    final_score: float


def time_decay(age_days: float) -> float:
    return math.exp(-settings.recommendation_time_decay_lambda * max(0.0, age_days))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Vectors must have equal non-zero dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


class RecommendationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._weights = {
            InteractionType.VIEW: settings.recommendation_interaction_view_weight,
            InteractionType.CLICK: settings.recommendation_interaction_click_weight,
            InteractionType.LIKE: settings.recommendation_interaction_like_weight,
            InteractionType.SAVE: settings.recommendation_interaction_save_weight,
            InteractionType.REGISTER: settings.recommendation_interaction_register_weight,
            InteractionType.SEARCH: 0.0,
        }

    async def build_user_profile(self, user_id: int) -> list[float] | None:
        rows = await self.db.execute(
            select(Interaction, Event.embedding)
            .join(Event, Event.id == Interaction.event_id)
            .where(Interaction.user_id == user_id, Event.embedding.is_not(None))
        )
        now = datetime.now(UTC)
        embeddings: list[list[float]] = []
        weights: list[float] = []
        for interaction, embedding in rows:
            base_weight = self._weights[interaction.interaction_type]
            if base_weight <= 0:
                continue
            age_days = max(0.0, (now - interaction.created_at).total_seconds() / 86400)
            weight = base_weight * time_decay(age_days)
            embeddings.append(list(embedding))
            weights.append(weight)
        return generate_user_profile_embedding(embeddings, weights)

    async def generate_candidates(
        self, user_id: int, profile_vector: list[float] | None
    ) -> list[Event]:
        registered = select(Interaction.event_id).where(
            Interaction.user_id == user_id,
            Interaction.interaction_type == InteractionType.REGISTER,
        )
        now = datetime.now(UTC)
        query: Select[tuple[Event]] = select(Event).where(
            Event.status == EventStatus.PUBLISHED,
            Event.start_time > now,
            ~Event.id.in_(registered),
        )
        if profile_vector is not None:
            query = query.where(Event.embedding.is_not(None)).order_by(
                Event.embedding.cosine_distance(profile_vector)
            )
        else:
            query = query.order_by(Event.start_time.asc())
        query = query.limit(settings.recommendation_candidate_limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _interest_names(self, user_id: int) -> set[str]:
        result = await self.db.execute(
            select(Interest.name, Interest.category)
            .join(UserInterest, UserInterest.interest_id == Interest.id)
            .where(UserInterest.user_id == user_id)
        )
        values: set[str] = set()
        for name, category in result:
            values.add(name.casefold())
            values.add(category.casefold())
        return values

    async def _behavior_scores(self, user_id: int, event_ids: list[int]) -> dict[int, float]:
        if not event_ids:
            return {}
        result = await self.db.execute(
            select(Interaction.event_id, Interaction.interaction_type, Interaction.created_at).where(
                Interaction.user_id == user_id, Interaction.event_id.in_(event_ids)
            )
        )
        now = datetime.now(UTC)
        scores: dict[int, float] = {}
        for event_id, interaction_type, created_at in result:
            age_days = max(0.0, (now - created_at).total_seconds() / 86400)
            score = self._weights[interaction_type] * time_decay(age_days)
            scores[event_id] = scores.get(event_id, 0.0) + score
        maximum = max(scores.values(), default=0.0)
        return {key: value / maximum for key, value in scores.items()} if maximum else {}

    async def rank(
        self, user_id: int, events: list[Event], profile_vector: list[float] | None
    ) -> list[RecommendationFeatures]:
        interests = await self._interest_names(user_id)
        behavior_scores = await self._behavior_scores(user_id, [event.id for event in events])
        popularity_result = await self.db.execute(
            select(Interaction.event_id, func.count(Interaction.id))
            .where(Interaction.event_id.in_([event.id for event in events]))
            .group_by(Interaction.event_id)
        )
        popularity = dict(popularity_result.all())
        max_popularity = max(popularity.values(), default=0)
        now = datetime.now(UTC)
        features: list[RecommendationFeatures] = []
        for event in events:
            semantic_score = 0.0
            if profile_vector is not None and event.embedding is not None:
                vector = list(event.embedding)
                semantic_score = max(0.0, min(1.0, (cosine_similarity(profile_vector, vector) + 1.0) / 2.0))
            event_terms = {event.category.casefold()} if event.category else set()
            event_terms.update(tag.casefold() for tag in event.tags)
            interest_score = 1.0 if interests.intersection(event_terms) else 0.0
            age_days = max(0.0, (now - event.created_at).total_seconds() / 86400)
            recency_score = math.exp(-0.05 * age_days)
            popularity_score = popularity.get(event.id, 0) / max_popularity if max_popularity else 0.0
            behavior_score = behavior_scores.get(event.id, 0.0)
            final_score = (
                settings.recommendation_semantic_weight * semantic_score
                + settings.recommendation_interest_weight * interest_score
                + settings.recommendation_behavior_weight * behavior_score
                + settings.recommendation_popularity_weight * popularity_score
                + settings.recommendation_recency_weight * recency_score
            )
            features.append(
                RecommendationFeatures(
                    event,
                    semantic_score,
                    interest_score,
                    behavior_score,
                    popularity_score,
                    recency_score,
                    final_score,
                )
            )
        return sorted(features, key=lambda item: (-item.final_score, item.event.start_time))

    async def recommend(self, user_id: int, limit: int = 10) -> list[RecommendationFeatures]:
        profile = await self.build_user_profile(user_id)
        candidates = await self.generate_candidates(user_id, profile)
        return (await self.rank(user_id, candidates, profile))[:limit]
