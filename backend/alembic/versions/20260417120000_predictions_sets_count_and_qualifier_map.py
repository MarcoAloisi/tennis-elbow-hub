"""predictions_sets_count_and_qualifier_map

Adds qualifier_map column to prediction_tournaments and migrates existing
prediction_entries.picks from old exact-score format ({winner, score}) to the
new sets-count format ({winner, sets_count, retirement}).

Revision ID: 20260417120000
Revises: 20260414220907
Create Date: 2026-04-17 12:00:00

"""
from __future__ import annotations

import json
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260417120000"
down_revision: Union[str, Sequence[str], None] = "20260414220907"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _count_sets_from_score(score: str | None) -> tuple[int, bool]:
    """Count completed sets in a legacy score string and detect retirement.

    Returns (sets_count, retirement).
    """
    if not score:
        return 0, False
    s = score.strip()
    retirement = False
    if re.search(r"ret\.?$", s, re.IGNORECASE):
        retirement = True
        s = re.sub(r"\s+ret\.?$", "", s, flags=re.IGNORECASE).strip()
    if re.fullmatch(r"w\.?o\.?", s, re.IGNORECASE) or s.upper() == "WO":
        return 0, True
    s = s.replace("-", "/")
    s = re.sub(r"\(\d+\)", "", s)
    count = 0
    for token in s.split():
        m = re.fullmatch(r"(\d+)/(\d+)", token.strip())
        if m and max(int(m.group(1)), int(m.group(2))) >= 6:
            count += 1
    return count, retirement


def _migrate_picks(picks_raw: object) -> dict:
    """Rewrite legacy picks dict into new format.

    Old: {match_id: {winner, score?}}
    New: {match_id: {winner, sets_count?, retirement?}}
    """
    if isinstance(picks_raw, str):
        try:
            picks = json.loads(picks_raw)
        except Exception:
            return {}
    elif isinstance(picks_raw, dict):
        picks = picks_raw
    else:
        return {}

    out: dict = {}
    for match_id, pick in picks.items():
        if not isinstance(pick, dict):
            continue
        new_pick: dict = {"winner": pick.get("winner", "")}
        if "sets_count" in pick and pick["sets_count"] in (2, 3, 4, 5):
            new_pick["sets_count"] = pick["sets_count"]
        if pick.get("retirement"):
            new_pick["retirement"] = True
        if "sets_count" not in new_pick and "retirement" not in new_pick:
            sets_count, retirement = _count_sets_from_score(pick.get("score"))
            if retirement:
                new_pick["retirement"] = True
            elif 2 <= sets_count <= 5:
                new_pick["sets_count"] = sets_count
        out[match_id] = new_pick
    return out


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    insp = inspect(conn)

    if "prediction_tournaments" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("prediction_tournaments")]
        if "qualifier_map" not in cols:
            op.add_column(
                "prediction_tournaments",
                sa.Column("qualifier_map", sa.JSON(), nullable=True),
            )

    if "prediction_entries" in insp.get_table_names():
        rows = conn.execute(sa.text("SELECT id, picks FROM prediction_entries")).fetchall()
        for row in rows:
            entry_id = row[0]
            picks_raw = row[1]
            new_picks = _migrate_picks(picks_raw)
            if dialect == "postgresql":
                conn.execute(
                    sa.text("UPDATE prediction_entries SET picks = CAST(:p AS JSON) WHERE id = :id"),
                    {"p": json.dumps(new_picks), "id": entry_id},
                )
            else:
                conn.execute(
                    sa.text("UPDATE prediction_entries SET picks = :p WHERE id = :id"),
                    {"p": json.dumps(new_picks), "id": entry_id},
                )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "prediction_tournaments" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("prediction_tournaments")]
        if "qualifier_map" in cols:
            op.drop_column("prediction_tournaments", "qualifier_map")
