"""add interests and user-interest relationships

Revision ID: 0002_auth_interests
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_auth_interests"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("category", sa.String(length=100), nullable=False),
    )
    op.create_table(
        "user_interests",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("interest_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interest_id"], ["interests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "interest_id"),
        sa.UniqueConstraint("user_id", "interest_id", name="uq_user_interest"),
    )


def downgrade() -> None:
    op.drop_table("user_interests")
    op.drop_table("interests")
