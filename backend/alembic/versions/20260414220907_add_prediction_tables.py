"""add_prediction_tables

Revision ID: 20260414220907
Revises: c64faa9b157b
Create Date: 2026-04-14 22:09:07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260414220907"
down_revision: Union[str, Sequence[str], None] = "c64faa9b157b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = inspect(conn).get_table_names()

    if "prediction_tournaments" not in existing:
        op.create_table(
            "prediction_tournaments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(250), nullable=False),
            sa.Column("managames_url", sa.String(500), nullable=False),
            sa.Column("trn_id", sa.Integer(), nullable=False),
            sa.Column("draw_data", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("predictions_close_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_prediction_tournaments_id"), "prediction_tournaments", ["id"], unique=False)
        op.create_index(op.f("ix_prediction_tournaments_slug"), "prediction_tournaments", ["slug"], unique=True)

    if "prediction_entries" not in existing:
        op.create_table(
            "prediction_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tournament_id", sa.Integer(), nullable=False),
            sa.Column("nickname", sa.String(30), nullable=False),
            sa.Column("ip_address", sa.String(45), nullable=False),
            sa.Column("picks", sa.JSON(), nullable=False),
            sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["tournament_id"], ["prediction_tournaments.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tournament_id", "ip_address", name="uq_entry_tournament_ip"),
            sa.UniqueConstraint("tournament_id", "nickname", name="uq_entry_tournament_nickname"),
        )
        op.create_index(op.f("ix_prediction_entries_id"), "prediction_entries", ["id"], unique=False)
        op.create_index(op.f("ix_prediction_entries_tournament_id"), "prediction_entries", ["tournament_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_prediction_entries_tournament_id"), table_name="prediction_entries")
    op.drop_index(op.f("ix_prediction_entries_id"), table_name="prediction_entries")
    op.drop_table("prediction_entries")
    op.drop_index(op.f("ix_prediction_tournaments_slug"), table_name="prediction_tournaments")
    op.drop_index(op.f("ix_prediction_tournaments_id"), table_name="prediction_tournaments")
    op.drop_table("prediction_tournaments")
