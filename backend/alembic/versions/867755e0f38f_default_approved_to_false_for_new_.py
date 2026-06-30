"""default approved to false for new signups

Revision ID: 867755e0f38f
Revises: 07c6bb4c1a08
Create Date: 2026-06-30 15:26:25.766573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '867755e0f38f'
down_revision: Union[str, Sequence[str], None] = '07c6bb4c1a08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("user_profiles", "approved", server_default="false")


def downgrade() -> None:
    op.alter_column("user_profiles", "approved", server_default="true")
