from functools import lru_cache

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
