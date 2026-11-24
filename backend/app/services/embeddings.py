import hashlib
import math
import re


_DIMENSIONS = 384
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def build_event_text(title: str, description: str, location: str | None = None) -> str:
    parts = [title, description]
    if location:
        parts.append(f"Location: {location}")
    return "\n".join(parts)


def embed_text(text: str) -> list[float]:
    vector = [0.0] * _DIMENSIONS
    tokens = _TOKEN_PATTERN.findall(text.casefold())
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for offset in range(0, len(digest), 2):
            dimension = int.from_bytes(digest[offset : offset + 2], "big") % _DIMENSIONS
            sign = 1.0 if digest[offset] & 1 else -1.0
            vector[dimension] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


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
    dimensions = len(event_embeddings[0])
    if any(len(vector) != dimensions for vector in event_embeddings):
        return None

    weight_total = sum(weights)
    if weight_total <= 0:
        return None
    weighted = [0.0] * dimensions
    for vector, weight in zip(event_embeddings, weights):
        for index, value in enumerate(vector):
            weighted[index] += value * weight
    weighted = [value / weight_total for value in weighted]

    norm = math.sqrt(sum(value * value for value in weighted))
    if norm == 0:
        return None
    return [value / norm for value in weighted]
