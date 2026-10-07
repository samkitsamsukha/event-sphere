from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


def build_event_text(title: str, description: str, location: str | None = None) -> str:
    parts = [title, description]
    if location:
        parts.append(f"Location: {location}")
    return "\n".join(parts)


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def generate_event_embedding(event_semantic_text: str) -> list[float]:
    embedding = embed_text(event_semantic_text)
    if len(embedding) != 384:
        raise ValueError("Event embedding model must produce exactly 384 dimensions")
    return embedding


def generate_user_profile_embedding(
    event_embeddings: list[list[float]], weights: list[float]
) -> list[float] | None:
    if not event_embeddings or not weights or len(event_embeddings) != len(weights):
        return None
    vectors = np.asarray(event_embeddings, dtype=np.float32)
    weighted = np.average(vectors, axis=0, weights=np.asarray(weights, dtype=np.float32))
    norm = np.linalg.norm(weighted)
    if norm == 0:
        return None
    return (weighted / norm).tolist()
