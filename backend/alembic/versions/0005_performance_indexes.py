"""add production search and vector indexes

Revision ID: 0005_performance_indexes
Revises: 0004_interactions
"""

from alembic import op

revision = "0005_performance_indexes"
down_revision = "0004_interactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_events_public_schedule",
        "events",
        ["status", "start_time"],
        postgresql_concurrently=False,
    )
    op.create_index(
        "ix_events_category",
        "events",
        ["category"],
        postgresql_concurrently=False,
    )
    op.execute(
        "CREATE INDEX ix_events_search_trgm ON events USING gin "
        "(semantic_text gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_events_embedding_hnsw ON events USING hnsw "
        "(embedding vector_cosine_ops)"
    )
    op.create_index(
        "ix_interactions_user_type_created",
        "interactions",
        ["user_id", "interaction_type", "created_at"],
    )
    op.create_index(
        "ix_interactions_event_type",
        "interactions",
        ["event_id", "interaction_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_interactions_event_type", table_name="interactions")
    op.drop_index("ix_interactions_user_type_created", table_name="interactions")
    op.execute("DROP INDEX ix_events_embedding_hnsw")
    op.execute("DROP INDEX ix_events_search_trgm")
    op.drop_index("ix_events_category", table_name="events")
    op.drop_index("ix_events_public_schedule", table_name="events")
