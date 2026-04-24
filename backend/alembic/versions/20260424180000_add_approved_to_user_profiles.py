"""add approved to user_profiles

Revision ID: 20260424180000
Revises: 5ff7f62c0348
Create Date: 2026-04-24 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260424180000"
down_revision = "5ff7f62c0348"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("approved", sa.Boolean(), server_default="true", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "approved")
