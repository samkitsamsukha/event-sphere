"""add event discovery fields

Revision ID: 0003_event_discovery_fields
Revises: 0002_auth_interests
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_event_discovery_fields"
down_revision = "0002_auth_interests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("category", sa.String(length=100), nullable=True))
    op.add_column(
        "events",
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
    )
    op.execute("UPDATE events SET semantic_text = '' WHERE semantic_text IS NULL")
    op.alter_column("events", "semantic_text", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    op.alter_column("events", "semantic_text", existing_type=sa.Text(), nullable=True)
    op.drop_column("events", "tags")
    op.drop_column("events", "category")
