from app.models.event import Event


def build_semantic_text(
    *,
    title: str,
    description: str,
    category: str | None,
    tags: list[str],
    location: str | None,
) -> str:
    parts = [
        f"Title: {title}",
        f"Description: {description}",
        f"Category: {category or ''}",
        f"Tags: {', '.join(tags)}",
        f"Location: {location or ''}",
    ]
    return " | ".join(parts)


def update_event_semantic_text(event: Event) -> None:
    event.semantic_text = build_semantic_text(
        title=event.title,
        description=event.description,
        category=event.category,
        tags=event.tags,
        location=event.location,
    )
