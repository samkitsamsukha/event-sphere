"""add behavioral interactions

Revision ID: 0004_interactions
Revises: 0003_event_discovery_fields
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_interactions"
down_revision = "0003_event_discovery_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    interaction_type = sa.Enum(
        "VIEW", "CLICK", "SEARCH", "LIKE", "SAVE", "REGISTER", name="interaction_type"
    )
    interaction_type.create(op.get_bind(), checkfirst=True)
    interaction_type_column = sa.Enum(
        "VIEW", "CLICK", "SEARCH", "LIKE", "SAVE", "REGISTER",
        name="interaction_type", create_type=False
    )
    op.create_table(
        "interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("interaction_type", interaction_type_column, nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_interactions_user_id", "interactions", ["user_id"])
    op.create_index("ix_interactions_event_id", "interactions", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_interactions_event_id", table_name="interactions")
    op.drop_index("ix_interactions_user_id", table_name="interactions")
    op.drop_table("interactions")
    sa.Enum(name="interaction_type").drop(op.get_bind(), checkfirst=True)
