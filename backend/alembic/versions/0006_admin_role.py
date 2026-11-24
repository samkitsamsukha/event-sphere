"""add admin user role

Revision ID: 0006_admin_role
Revises: 0005_performance_indexes
"""

from alembic import op

revision = "0006_admin_role"
down_revision = "0005_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'ADMIN'")


def downgrade() -> None:
    # PostgreSQL does not support removing an enum value safely in place.
    pass
