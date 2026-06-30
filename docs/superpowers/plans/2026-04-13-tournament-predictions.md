# Tournament Predictions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an XKT tournament prediction game at `/online-tours/xkt/predictions` where users anonymously predict bracket outcomes, scored on exact scores, with a live leaderboard and historical archive.

**Architecture:** Two new SQLAlchemy models (`PredictionTournament`, `PredictionEntry`), a standalone scoring engine, a managames HTML scraper, and 9 FastAPI endpoints. The frontend uses a new Pinia store, a bracket editor built from composable Vue components, and a dedicated route under the existing XKT tour.

**Tech Stack:** FastAPI, SQLAlchemy async, BeautifulSoup4, httpx (backend) · Vue 3 + Pinia, TypeScript (frontend)

---

## File Map

### New files
| Path | Responsibility |
|------|---------------|
| `backend/app/models/prediction.py` | ORM models + Pydantic schemas for PredictionTournament and PredictionEntry |
| `backend/app/services/scoring.py` | Pure scoring functions: parse score strings, compute match points |
| `backend/app/services/tournament_scraper.py` | Async httpx + BeautifulSoup scraper for managames OT_ViewTournament.php |
| `backend/app/api/endpoints/predictions.py` | All 9 prediction API endpoints |
| `backend/tests/test_scoring.py` | Unit tests for scoring engine |
| `frontend/src/stores/predictions.ts` | Pinia store: state, API calls, localStorage token management |
| `frontend/src/components/predictions/BracketMatch.vue` | Single match cell: two clickable players + optional score input |
| `frontend/src/components/predictions/BracketEditor.vue` | Full interactive bracket grid (left-to-right rounds, TBD propagation) |
| `frontend/src/components/predictions/PredictionLeaderboard.vue` | Ranked table + podium (shown after tournament finishes) |
| `frontend/src/components/predictions/AllPredictions.vue` | Table of all entries; clicking a row shows that user's bracket read-only |
| `frontend/src/components/predictions/AdminPanel.vue` | Admin-only controls: add tournament, refresh, close, finish, delete entry |
| `frontend/src/views/PredictionView.vue` | Top-level view: tournament banner, tabs, archive grid |

### Modified files
| Path | Change |
|------|--------|
| `backend/app/api/router.py` | `include_router(predictions.router)` |
| `frontend/src/router/index.ts` | Add `/online-tours/xkt/predictions` route |
| `frontend/src/views/OnlineToursView.vue` | Add "Tournament Predictions →" card to XKT tab |

---

## Task 1: Backend models

**Files:**
- Create: `backend/app/models/prediction.py`

- [ ] **Step 1: Create the model file**

```python
# backend/app/models/prediction.py
"""ORM models and Pydantic schemas for Tournament Predictions."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.core.database import Base


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class PredictionTournament(Base):
    __tablename__ = "prediction_tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), nullable=False, unique=True, index=True)
    managames_url: Mapped[str] = mapped_column(String(500), nullable=False)
    trn_id: Mapped[int] = mapped_column(Integer, nullable=False)
    draw_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    predictions_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    entries: Mapped[list["PredictionEntry"]] = relationship(
        "PredictionEntry", back_populates="tournament", cascade="all, delete-orphan"
    )


class PredictionEntry(Base):
    __tablename__ = "prediction_entries"
    __table_args__ = (
        UniqueConstraint("tournament_id", "ip_address", name="uq_entry_tournament_ip"),
        UniqueConstraint("tournament_id", "nickname", name="uq_entry_tournament_nickname"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("prediction_tournaments.id"), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(30), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    picks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tournament: Mapped["PredictionTournament"] = relationship("PredictionTournament", back_populates="entries")


# ─── Pydantic Schemas ───────────────────────────────────────────────────────

class TournamentCreate(BaseModel):
    managames_url: str
    predictions_close_at: datetime


class TournamentResponse(BaseModel):
    id: int
    name: str
    slug: str
    managames_url: str
    trn_id: int
    draw_data: dict
    status: str
    predictions_close_at: datetime
    created_at: datetime
    updated_at: datetime
    entry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TournamentListItem(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    predictions_close_at: datetime
    created_at: datetime
    entry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class EntryCreate(BaseModel):
    nickname: str
    picks: dict  # {match_id: {winner: str, score?: str}}


class EntryResponse(BaseModel):
    id: int
    tournament_id: int
    nickname: str
    picks: dict
    total_score: int
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Register models so `init_db` picks them up**

Open `backend/app/models/__init__.py` and add the import:

```python
# backend/app/models/__init__.py  (add this line)
from app.models.prediction import PredictionTournament, PredictionEntry  # noqa: F401
```

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/models/prediction.py app/models/__init__.py
git commit -m "feat: add PredictionTournament and PredictionEntry models"
```

---

## Task 2: Scoring engine (TDD)

**Files:**
- Create: `backend/app/services/scoring.py`
- Create: `backend/tests/test_scoring.py`

- [ ] **Step 1: Write the failing tests first**

```python
# backend/tests/test_scoring.py
"""Unit tests for the tournament prediction scoring engine."""
import pytest
from app.services.scoring import compute_match_score, parse_score, ROUND_POINTS


class TestParseScore:
    def test_two_set_straight(self):
        assert parse_score("6/3 6/2") == ["6/3", "6/2"]

    def test_three_set_match(self):
        assert parse_score("6/3 3/6 7/5") == ["6/3", "3/6", "7/5"]

    def test_tiebreak_notation_stripped(self):
        # 7/6(3) normalises to 7/6 for comparison
        assert parse_score("7/6(3) 6/4") == ["7/6", "6/4"]

    def test_dash_separator(self):
        assert parse_score("6-3 6-2") == ["6/3", "6/2"]

    def test_empty_string(self):
        assert parse_score("") == []

    def test_none(self):
        assert parse_score(None) == []

    def test_walkover_returns_empty(self):
        assert parse_score("WO") == []
        assert parse_score("w.o.") == []

    def test_retired_returns_partial(self):
        # ret. / ret scores still count the completed sets
        assert parse_score("6/3 2/1 ret.") == ["6/3"]


class TestComputeMatchScore:
    def test_wrong_winner_zero(self):
        assert compute_match_score("R1", "PlayerA", "PlayerB", None, None) == 0

    def test_match_not_played_zero(self):
        assert compute_match_score("R1", "PlayerA", None, None, None) == 0

    def test_winner_only_no_score(self):
        assert compute_match_score("R1", "Jira", "Jira", None, None) == 5
        assert compute_match_score("SF", "Jira", "Jira", None, None) == 30
        assert compute_match_score("F", "Jira", "Jira", None, None) == 50

    def test_winner_with_unparseable_score(self):
        assert compute_match_score("R1", "Jira", "Jira", "WO", "6/3 6/2") == 5

    def test_exact_score_r1(self):
        assert compute_match_score("R1", "Jira", "Jira", "6/3 6/2", "6/3 6/2") == 30

    def test_exact_score_final(self):
        assert compute_match_score("F", "Jira", "Jira", "6/3 3/6 7/5", "6/3 3/6 7/5") == 200

    def test_correct_sets_count_straight(self):
        # predicted 2 sets, actual 2 sets — correct sets count
        score = compute_match_score("R1", "Jira", "Jira", "6/1 6/0", "6/3 6/2")
        assert score == 15  # sets count pts, no individual set bonus (both wrong)

    def test_correct_sets_count_plus_partial(self):
        # predicted 6/3 3/6 7/5, actual 6/3 3/6 6/1 — correct sets count, 2 sets right
        score = compute_match_score("SF", "Jira", "Jira", "6/3 3/6 7/5", "6/3 3/6 6/1")
        assert score == 75 + 3 + 3  # sets pts + 2 correct sets * 3

    def test_wrong_sets_count_winner_only_plus_partial(self):
        # predicted 2 sets, actual 3 sets — wrong sets count
        score = compute_match_score("R1", "Jira", "Jira", "6/3 6/2", "6/3 3/6 6/4")
        assert score == 5 + 3  # winner pts + 1 correct set (6/3)

    def test_tiebreak_normalized_in_comparison(self):
        # 7/6 should match 7/6(3)
        score = compute_match_score("QF", "Jira", "Jira", "7/6 6/4", "7/6(3) 6/4")
        assert score == 100  # exact

    def test_unknown_round_defaults_to_r1(self):
        score = compute_match_score("Q2", "Jira", "Jira", None, None)
        assert score == 0  # qualifying not scored
```

- [ ] **Step 2: Run tests — confirm all fail (module not found)**

```bash
cd backend
python -m pytest tests/test_scoring.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'app.services.scoring'`

- [ ] **Step 3: Implement the scoring engine**

```python
# backend/app/services/scoring.py
"""Pure scoring functions for tournament predictions.

Scoring rules:
- Wrong winner → 0 pts
- Match not played yet → 0 pts
- Qualifying rounds (Q1, Q2) → 0 pts (not scored)
- Correct winner, no score / unparseable → winner-only base pts
- Correct sets count + all sets exact → exact score pts
- Correct sets count + some sets exact → sets-count pts + 3 per correct set
- Wrong sets count + some sets match → winner-only pts + 3 per correct set
"""

from __future__ import annotations

import re

# (winner_only, correct_sets_count, exact_score)
ROUND_POINTS: dict[str, tuple[int, int, int]] = {
    "R1": (5, 15, 30),
    "R2": (10, 25, 50),
    "R3": (15, 35, 70),
    "QF": (20, 50, 100),
    "SF": (30, 75, 150),
    "F": (50, 100, 200),
}

# Rounds that are NOT scored (qualifying)
_UNSCORED_ROUNDS = {"Q1", "Q2", "Qualified"}


def parse_score(score: str | None) -> list[str]:
    """Parse a score string into a list of normalised set scores.

    Handles formats like '6/3 6/2', '6-3 6-2', '7/6(3) 6/4', '6/3 2/1 ret.'.
    Tiebreak annotations (e.g. '(3)') are stripped for comparison.
    Walkover / w.o. / WO returns [].
    Only fully completed sets are returned (ret. mid-set is dropped).

    Args:
        score: Raw score string from managames or user input.

    Returns:
        List of normalised set score strings like ['6/3', '7/6', '3/6'].
    """
    if not score:
        return []

    score = score.strip()

    # Strip ret./retirement suffix — keep only what came before
    score = re.sub(r"\s+ret\.?$", "", score, flags=re.IGNORECASE).strip()

    # Walkover / w.o. — no sets
    if re.fullmatch(r"w\.?o\.?", score, re.IGNORECASE) or score.upper() == "WO":
        return []

    # Normalise: replace dashes with slashes, strip tiebreak annotations
    score = score.replace("-", "/")
    score = re.sub(r"\(\d+\)", "", score)  # remove (3), (6) etc.

    sets = []
    for token in score.split():
        token = token.strip()
        if re.fullmatch(r"\d+/\d+", token):
            sets.append(token)

    return sets


def compute_match_score(
    round_name: str,
    predicted_winner: str,
    actual_winner: str | None,
    predicted_score: str | None,
    actual_score: str | None,
) -> int:
    """Compute points for one match prediction.

    Args:
        round_name: e.g. 'R1', 'QF', 'F'. Qualifying rounds score 0.
        predicted_winner: Nickname the user picked to win.
        actual_winner: Actual winner from managames (None if not played).
        predicted_score: User-provided score string (may be None).
        actual_score: Actual score from managames (None if not played).

    Returns:
        Points earned for this match (0 if wrong winner or not yet played).
    """
    if round_name in _UNSCORED_ROUNDS:
        return 0
    if actual_winner is None:
        return 0
    if predicted_winner != actual_winner:
        return 0

    pts_winner, pts_sets, pts_exact = ROUND_POINTS.get(round_name, (5, 15, 30))

    pred_sets = parse_score(predicted_score)
    actual_sets = parse_score(actual_score)

    if not pred_sets or not actual_sets:
        return pts_winner

    # Per-set partial credit
    per_set_bonus = sum(3 for p, a in zip(pred_sets, actual_sets) if p == a)

    if pred_sets == actual_sets:
        return pts_exact  # exact match — max points

    if len(pred_sets) == len(actual_sets):
        # Correct sets count, not exact
        return pts_sets + per_set_bonus

    # Wrong sets count — winner only + partial
    return pts_winner + per_set_bonus


def compute_entry_score(picks: dict, matches: list[dict]) -> int:
    """Compute total score for a prediction entry against actual draw results.

    Args:
        picks: {match_id: {"winner": str, "score": str | None}}
        matches: draw_data["matches"] list from PredictionTournament.

    Returns:
        Total points earned across all predicted matches.
    """
    match_map = {m["id"]: m for m in matches}
    total = 0
    for match_id, pick in picks.items():
        match = match_map.get(match_id)
        if not match:
            continue
        total += compute_match_score(
            round_name=match["round"],
            predicted_winner=pick.get("winner", ""),
            actual_winner=match.get("winner"),
            predicted_score=pick.get("score"),
            actual_score=match.get("score"),
        )
    return total
```

- [ ] **Step 4: Run tests — all must pass**

```bash
cd backend
python -m pytest tests/test_scoring.py -v
```
Expected: all 16 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/scoring.py tests/test_scoring.py
git commit -m "feat: add prediction scoring engine with full test coverage"
```

---

## Task 3: Tournament draw scraper

**Files:**
- Create: `backend/app/services/tournament_scraper.py`

- [ ] **Step 1: Create the scraper**

```python
# backend/app/services/tournament_scraper.py
"""Async scraper for managames OT_ViewTournament.php tournament draw pages.

Fetches and parses the bracket HTML into the draw_data JSON structure
used by PredictionTournament.draw_data.

draw_data shape:
{
    "name": "Monte-Carlo 2026 (Singles)",
    "surface": "Clay",
    "category": "Masters 1000",
    "draw_size": 64,
    "week": "15",
    "year": "2026",
    "matches": [
        {
            "id": "main_R1_0",
            "section": "main",
            "round": "R1",
            "player1": {"name": "Jira", "seed": 1, "player_id": "48100"},
            "player2": {"name": "MagRai", "seed": null, "player_id": "60880"},
            "winner": "Jira",       # null if not yet played
            "score": "6/0 6/0"      # null if not yet played
        },
        ...
    ]
}
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger

logger = get_logger("tournament_scraper")

# Maps abbreviated column headers to canonical round names
_ROUND_MAP: dict[str, str] = {
    "Q1": "Q1", "Q2": "Q2", "Qualified": "Qualified",
    "R1": "R1", "R2": "R2", "R3": "R3",
    "Q": "QF",   # managames uses Q for quarterfinals
    "S": "SF",   # and S for semifinals
    "F": "F",
    "W": "W",    # winner column — skip, it's just repeated winner info
}


def _extract_trn_id(url: str) -> int:
    """Extract the Trn= query parameter from a managames URL."""
    qs = parse_qs(urlparse(url).query)
    trn_values = qs.get("Trn", [])
    if not trn_values:
        raise ValueError(f"No Trn parameter found in URL: {url}")
    return int(trn_values[0])


def _parse_player_cell(td: Tag) -> dict | None:
    """Extract player info from a draw table <td> cell.

    Returns dict with keys: name, seed, player_id.
    Returns None for empty or TBD cells.
    """
    if td is None:
        return None

    # Check for player link
    link = td.find("a", href=re.compile(r"OT_Player\.php"))
    if link:
        name = link.get_text(strip=True)
        href = link.get("href", "")
        pid_match = re.search(r"p=(\d+)", href)
        player_id = pid_match.group(1) if pid_match else None

        # Seed: appears as "(N)" text immediately after the link
        full_text = td.get_text()
        seed_match = re.search(r"\((\d+)\)", full_text)
        seed = int(seed_match.group(1)) if seed_match else None

        return {"name": name, "seed": seed, "player_id": player_id}

    # Check for TBD / Bye text
    text = td.get_text(strip=True)
    if text in ("TBD", "Bye", ""):
        return {"name": "TBD", "seed": None, "player_id": None}

    return None


def _parse_score_cell(td: Tag) -> str | None:
    """Extract the match score from a result cell."""
    score_span = td.find("span", class_="score")
    if score_span:
        score = score_span.get_text(strip=True)
        return score if score else None
    return None


def _build_virtual_grid(table: Tag) -> list[list[dict | None]]:
    """Build a (row, col) grid from a draw table accounting for rowspan.

    Each cell is either None (empty/spanned) or a dict:
        {"td": Tag, "rowspan": int}
    """
    rows = table.find_all("tr")
    grid: list[list[dict | None]] = []
    # Track pending rowspans: col_idx -> remaining_rows
    pending: dict[int, int] = {}

    for row in rows:
        cells = row.find_all("td")
        grid_row: list[dict | None] = []
        cell_iter = iter(cells)

        col = 0
        cell = next(cell_iter, None)

        while col < 20 or cell is not None:  # generous column limit
            if col in pending and pending[col] > 0:
                # This column is covered by a rowspan from a previous row
                grid_row.append(None)
                pending[col] -= 1
                if pending[col] == 0:
                    del pending[col]
                col += 1
            elif cell is not None:
                rs = int(cell.get("rowspan", 1))
                grid_row.append({"td": cell, "rowspan": rs})
                if rs > 1:
                    pending[col] = rs - 1
                col += 1
                cell = next(cell_iter, None)
            else:
                break

        grid.append(grid_row)

    return grid


def _parse_draw_table(table: Tag, section: str) -> list[dict]:
    """Parse one draw table (main or qualifying) into a list of match dicts."""
    # Extract round headers from <thead>
    thead = table.find("thead")
    if not thead:
        return []

    headers = [th.get_text(strip=True) for th in thead.find_all("th", class_="Large")]
    rounds = [_ROUND_MAP.get(h) for h in headers]

    # Skip "W" (winner column) and points/date rows — only parse player/result rows
    grid = _build_virtual_grid(table)

    # Filter out header rows (they have class="Points" cells or all-header content)
    data_rows = []
    for row in grid:
        # Skip rows that are all None or contain only points/date cells
        has_player_content = False
        for cell in row:
            if cell and cell["td"]:
                td = cell["td"]
                if "Points" not in (td.get("class") or []) and "Hidden" not in (td.get("class") or []):
                    has_player_content = True
                    break
        if has_player_content:
            data_rows.append(row)

    matches = []
    match_idx_per_round: dict[int, int] = {}

    # R1 players are in column 0 (one per row), R2 in column 1 (rowspan=2), etc.
    # For each round column, collect the cells that actually contain data
    num_rounds = len(rounds)
    for col_idx, round_name in enumerate(rounds):
        if round_name is None or round_name == "W":
            continue

        col_matches: list[tuple[Tag, Tag | None]] = []  # (player/winner_td, ?)
        seen_rows: set[int] = set()

        for row_idx, row in enumerate(data_rows):
            if col_idx >= len(row):
                continue
            cell = row[col_idx]
            if cell is None:
                continue
            if row_idx in seen_rows:
                continue

            td = cell["td"]
            rs = cell["rowspan"]
            # Mark all spanned rows as seen
            for r in range(row_idx, min(row_idx + rs, len(data_rows))):
                seen_rows.add(r)

            col_matches.append((td, rs, row_idx))

        # For R1: each cell is one player (appears in pairs as match)
        # For R2+: each cell is the winner of a match (rowspan covers that match's players)
        if col_idx == 0:
            # Pair up consecutive R1 cells into matches
            for i in range(0, len(col_matches) - 1, 2):
                td1, _, _ = col_matches[i]
                td2, _, _ = col_matches[i + 1]
                p1 = _parse_player_cell(td1)
                p2 = _parse_player_cell(td2)
                if p1 or p2:
                    idx = match_idx_per_round.get(col_idx, 0)
                    match_idx_per_round[col_idx] = idx + 1
                    matches.append({
                        "id": f"{section}_{round_name}_{idx}",
                        "section": section,
                        "round": round_name,
                        "player1": p1 or {"name": "TBD", "seed": None, "player_id": None},
                        "player2": p2 or {"name": "TBD", "seed": None, "player_id": None},
                        "winner": None,
                        "score": None,
                    })
        else:
            # Each cell in R2+ is a winner/result cell
            for td, rs, row_idx in col_matches:
                player_info = _parse_player_cell(td)
                score = _parse_score_cell(td)

                idx = match_idx_per_round.get(col_idx, 0)
                match_idx_per_round[col_idx] = idx + 1

                # Determine previous round name to link players
                prev_round = rounds[col_idx - 1] if col_idx > 0 else None

                matches.append({
                    "id": f"{section}_{round_name}_{idx}",
                    "section": section,
                    "round": round_name,
                    "player1": {"name": "TBD", "seed": None, "player_id": None},
                    "player2": {"name": "TBD", "seed": None, "player_id": None},
                    "winner": player_info["name"] if player_info and player_info["name"] != "TBD" else None,
                    "score": score,
                })

    return matches


def _parse_tournament_meta(soup: BeautifulSoup) -> dict:
    """Extract tournament metadata from the info table at the top."""
    meta = {"name": "Unknown", "surface": "", "category": "", "draw_size": 0, "week": "", "year": ""}

    # The page title contains name: "View Tournament: Monte-Carlo (Official Topic)"
    h2 = soup.find("h2")
    if h2:
        title_text = h2.get_text()
        name_match = re.search(r"View Tournament:\s*(.+?)(?:\s*\(|$)", title_text)
        if name_match:
            meta["name"] = name_match.group(1).strip()

    # Info table: first <table class="Ot"> after the <dt> with tournament name
    info_table = soup.find("table", class_="Ot")
    if info_table:
        headers = [th.get_text(strip=True) for th in info_table.find_all("th")]
        values_row = info_table.find("tr", class_=lambda c: c is None)
        if values_row:
            tds = values_row.find_all("td")
            row_vals = [td.get_text(strip=True) for td in tds]
            mapping = dict(zip(headers, row_vals))
            meta["surface"] = mapping.get("Surface", "")
            meta["category"] = mapping.get("Category", "")
            try:
                meta["draw_size"] = int(mapping.get("Draw", "0"))
            except ValueError:
                pass
            week_str = mapping.get("Week", "")
            meta["week"] = week_str.split("-")[0].strip() if week_str else ""
            meta["year"] = mapping.get("Year", "")

    return meta


async def scrape_tournament_draw(url: str) -> dict:
    """Fetch and parse a managames tournament page into draw_data.

    Args:
        url: Full URL of OT_ViewTournament.php page.

    Returns:
        draw_data dict ready to store in PredictionTournament.draw_data.

    Raises:
        httpx.HTTPError: If the page cannot be fetched.
        ValueError: If the page structure is unexpected.
    """
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
        headers={
            "User-Agent": "TennisElbowHub/1.0 (tournament predictions)",
            "Accept": "text/html,*/*",
        },
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    meta = _parse_tournament_meta(soup)

    # Find all draw sections by their <dt> label
    all_matches: list[dict] = []
    for dt in soup.find_all("dt"):
        label = dt.get_text(strip=True)
        if label == "Main Draw":
            # Main draw may be split across multiple OtScrollableContainer divs
            parent_dl = dt.parent
            for container in parent_dl.find_all("div", class_="OtScrollableContainer"):
                table = container.find("table", class_="Ot")
                if table:
                    all_matches.extend(_parse_draw_table(table, "main"))
        elif label == "Qualifications":
            parent_dl = dt.parent
            table = parent_dl.find("table", class_="Ot")
            if table:
                all_matches.extend(_parse_draw_table(table, "qualifying"))

    return {
        "name": meta["name"],
        "surface": meta["surface"],
        "category": meta["category"],
        "draw_size": meta["draw_size"],
        "week": meta["week"],
        "year": meta["year"],
        "matches": all_matches,
    }
```

- [ ] **Step 2: Commit**

```bash
git add app/services/tournament_scraper.py
git commit -m "feat: add managames tournament draw scraper"
```

---

## Task 4: Backend API endpoints

**Files:**
- Create: `backend/app/api/endpoints/predictions.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Create the endpoints file**

```python
# backend/app/api/endpoints/predictions.py
"""Tournament Predictions API endpoints."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.models.prediction import (
    EntryCreate,
    EntryResponse,
    PredictionEntry,
    PredictionTournament,
    TournamentCreate,
    TournamentListItem,
    TournamentResponse,
    _slugify,
)
from app.services.scoring import compute_entry_score
from app.services.tournament_scraper import scrape_tournament_draw

logger = get_logger("api.predictions")
router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _unique_slug(db: AsyncSession, base: str) -> str:
    slug = base
    counter = 1
    while True:
        exists = (await db.execute(
            select(PredictionTournament).where(PredictionTournament.slug == slug)
        )).scalar_one_or_none()
        if not exists:
            return slug
        slug = f"{base}-{counter}"
        counter += 1


# ─── Public Endpoints ────────────────────────────────────────────────────────


@router.get("/tournaments", response_model=list[TournamentListItem])
@limiter.limit("60/minute")
async def list_tournaments(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all tournaments (active first, then by created_at desc)."""
    result = await db.execute(
        select(PredictionTournament).order_by(
            PredictionTournament.status.asc(),  # open < closed < finished alphabetically is wrong
            PredictionTournament.created_at.desc(),
        )
    )
    tournaments = result.scalars().all()

    out = []
    for t in tournaments:
        count_result = await db.execute(
            select(func.count(PredictionEntry.id)).where(PredictionEntry.tournament_id == t.id)
        )
        entry_count = count_result.scalar_one()
        item = TournamentListItem.model_validate(t)
        item.entry_count = entry_count
        out.append(item)

    return out


@router.get("/tournaments/{slug}", response_model=TournamentResponse)
@limiter.limit("60/minute")
async def get_tournament(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get tournament detail including full draw_data."""
    result = await db.execute(
        select(PredictionTournament).where(PredictionTournament.slug == slug)
    )
    tournament = result.scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    count_result = await db.execute(
        select(func.count(PredictionEntry.id)).where(PredictionEntry.tournament_id == tournament.id)
    )
    entry_count = count_result.scalar_one()

    out = TournamentResponse.model_validate(tournament)
    out.entry_count = entry_count
    return out


@router.get("/tournaments/{tournament_id}/entries", response_model=list[EntryResponse])
@limiter.limit("60/minute")
async def list_entries(
    request: Request,
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all prediction entries for a tournament, sorted by score desc."""
    result = await db.execute(
        select(PredictionEntry)
        .where(PredictionEntry.tournament_id == tournament_id)
        .order_by(PredictionEntry.total_score.desc(), PredictionEntry.submitted_at.asc())
    )
    return result.scalars().all()


@router.post(
    "/tournaments/{tournament_id}/entries",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def submit_entry(
    request: Request,
    tournament_id: int,
    body: EntryCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Submit a prediction entry (anonymous, one per IP per tournament)."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if tournament.status != "open":
        raise HTTPException(status_code=409, detail="Predictions are closed for this tournament")

    now = datetime.now(timezone.utc)
    close_at = tournament.predictions_close_at
    if close_at.tzinfo is None:
        from datetime import timezone as tz
        close_at = close_at.replace(tzinfo=tz.utc)
    if now > close_at:
        raise HTTPException(status_code=409, detail="Prediction deadline has passed")

    nickname = body.nickname.strip()[:30]
    if not nickname:
        raise HTTPException(status_code=400, detail="Nickname is required")

    ip = _get_client_ip(request)

    # IP lock
    ip_exists = (await db.execute(
        select(PredictionEntry).where(
            PredictionEntry.tournament_id == tournament_id,
            PredictionEntry.ip_address == ip,
        )
    )).scalar_one_or_none()
    if ip_exists:
        raise HTTPException(status_code=409, detail="A prediction from this IP already exists")

    # Nickname lock
    nick_exists = (await db.execute(
        select(PredictionEntry).where(
            PredictionEntry.tournament_id == tournament_id,
            PredictionEntry.nickname == nickname,
        )
    )).scalar_one_or_none()
    if nick_exists:
        raise HTTPException(status_code=409, detail="This nickname is already taken for this tournament")

    entry = PredictionEntry(
        tournament_id=tournament_id,
        nickname=nickname,
        ip_address=ip,
        picks=body.picks,
        total_score=0,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


# ─── Admin Endpoints ─────────────────────────────────────────────────────────


@router.post("/tournaments", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_tournament(
    request: Request,
    body: TournamentCreate,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a tournament by scraping a managames URL (Admin only)."""
    try:
        draw_data = await scrape_tournament_draw(body.managames_url)
    except Exception as exc:
        logger.exception("Failed to scrape tournament draw")
        raise HTTPException(status_code=422, detail=f"Failed to scrape draw: {exc}")

    name = draw_data.get("name", "Unknown Tournament")
    trn_id_match = re.search(r"Trn=(\d+)", body.managames_url)
    trn_id = int(trn_id_match.group(1)) if trn_id_match else 0

    slug = await _unique_slug(db, _slugify(name))

    tournament = PredictionTournament(
        name=name,
        slug=slug,
        managames_url=body.managames_url,
        trn_id=trn_id,
        draw_data=draw_data,
        status="open",
        predictions_close_at=body.predictions_close_at,
    )
    db.add(tournament)
    await db.commit()
    await db.refresh(tournament)

    out = TournamentResponse.model_validate(tournament)
    out.entry_count = 0
    return out


@router.post("/tournaments/{tournament_id}/refresh")
@limiter.limit("10/minute")
async def refresh_tournament(
    request: Request,
    tournament_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-scrape managames and recompute all entry scores (Admin only)."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    try:
        draw_data = await scrape_tournament_draw(tournament.managames_url)
    except Exception as exc:
        logger.exception("Failed to re-scrape draw")
        raise HTTPException(status_code=422, detail=f"Failed to re-scrape: {exc}")

    tournament.draw_data = draw_data
    await db.flush()

    # Recompute scores for all entries
    entries = (await db.execute(
        select(PredictionEntry).where(PredictionEntry.tournament_id == tournament_id)
    )).scalars().all()

    matches = draw_data.get("matches", [])
    for entry in entries:
        entry.total_score = compute_entry_score(entry.picks, matches)

    await db.commit()
    return {"refreshed": True, "entries_scored": len(entries)}


@router.post("/tournaments/{tournament_id}/close")
@limiter.limit("10/minute")
async def close_predictions(
    request: Request,
    tournament_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Close predictions (no new entries accepted) (Admin only)."""
    await db.execute(
        update(PredictionTournament)
        .where(PredictionTournament.id == tournament_id)
        .values(status="closed")
    )
    await db.commit()
    return {"status": "closed"}


@router.post("/tournaments/{tournament_id}/finish")
@limiter.limit("10/minute")
async def finish_tournament(
    request: Request,
    tournament_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark tournament as finished and reveal podium (Admin only)."""
    await db.execute(
        update(PredictionTournament)
        .where(PredictionTournament.id == tournament_id)
        .values(status="finished")
    )
    await db.commit()
    return {"status": "finished"}


@router.delete("/tournaments/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tournament(
    request: Request,
    tournament_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tournament and all its entries (Admin only)."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    await db.delete(tournament)
    await db.commit()


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    request: Request,
    entry_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a suspicious or duplicate entry (Admin only)."""
    entry = (await db.execute(
        select(PredictionEntry).where(PredictionEntry.id == entry_id)
    )).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)
    await db.commit()
```

- [ ] **Step 2: Wire into router**

Open `backend/app/api/router.py` and add:

```python
from app.api.endpoints import admin, contact, guides, live_scores, match_analysis, outfits, predictions, tour_logs

# ... existing includes ...
api_router.include_router(predictions.router)
```

- [ ] **Step 3: Verify server starts without errors**

```bash
cd backend
uvicorn app.main:app --reload 2>&1 | head -20
```
Expected: `Application startup complete.` with no import errors.

- [ ] **Step 4: Commit**

```bash
git add app/api/endpoints/predictions.py app/api/router.py
git commit -m "feat: add tournament predictions API endpoints"
```

---

## Task 5: Frontend Pinia store

**Files:**
- Create: `frontend/src/stores/predictions.ts`

- [ ] **Step 1: Create the store**

```typescript
// frontend/src/stores/predictions.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiUrl } from '@/config/api'
import { useAuthStore } from '@/stores/auth'

export interface PlayerInfo {
    name: string
    seed: number | null
    player_id: string | null
}

export interface DrawMatch {
    id: string
    section: 'main' | 'qualifying'
    round: string
    player1: PlayerInfo
    player2: PlayerInfo
    winner: string | null
    score: string | null
}

export interface DrawData {
    name: string
    surface: string
    category: string
    draw_size: number
    week: string
    year: string
    matches: DrawMatch[]
}

export interface Tournament {
    id: number
    name: string
    slug: string
    managames_url?: string
    trn_id?: number
    draw_data?: DrawData
    status: 'open' | 'closed' | 'finished'
    predictions_close_at: string
    created_at: string
    updated_at?: string
    entry_count: number
}

export interface PredictionEntry {
    id: number
    tournament_id: number
    nickname: string
    picks: Record<string, { winner: string; score?: string }>
    total_score: number
    submitted_at: string
}

export interface PickData {
    winner: string
    score?: string
}

const STORAGE_KEY_PREFIX = 'prediction_submitted_'
const STORAGE_NICK_KEY = 'prediction_nickname'

export const usePredictionsStore = defineStore('predictions', () => {
    const tournaments = ref<Tournament[]>([])
    const activeTournament = ref<Tournament | null>(null)
    const entries = ref<PredictionEntry[]>([])
    const myPicks = ref<Record<string, PickData>>({})
    const myNickname = ref<string>(localStorage.getItem(STORAGE_NICK_KEY) || '')
    const loading = ref(false)
    const error = ref<string | null>(null)

    // IDs of tournaments the user has submitted to (from localStorage)
    const submittedIds = computed<Set<number>>(() => {
        const ids = new Set<number>()
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i)
            if (key?.startsWith(STORAGE_KEY_PREFIX)) {
                const id = parseInt(key.replace(STORAGE_KEY_PREFIX, ''), 10)
                if (!isNaN(id)) ids.add(id)
            }
        }
        return ids
    })

    function hasSubmitted(tournamentId: number): boolean {
        return localStorage.getItem(`${STORAGE_KEY_PREFIX}${tournamentId}`) === '1'
    }

    function markSubmitted(tournamentId: number, nickname: string): void {
        localStorage.setItem(`${STORAGE_KEY_PREFIX}${tournamentId}`, '1')
        localStorage.setItem(STORAGE_NICK_KEY, nickname)
        myNickname.value = nickname
    }

    async function fetchTournaments(): Promise<void> {
        loading.value = true
        error.value = null
        try {
            const res = await fetch(apiUrl('/api/predictions/tournaments'))
            if (!res.ok) throw new Error(`Failed to load tournaments: ${res.statusText}`)
            tournaments.value = await res.json()
        } catch (err: any) {
            error.value = err.message
        } finally {
            loading.value = false
        }
    }

    async function fetchTournament(slug: string): Promise<void> {
        loading.value = true
        error.value = null
        try {
            const res = await fetch(apiUrl(`/api/predictions/tournaments/${slug}`))
            if (!res.ok) throw new Error(`Failed to load tournament: ${res.statusText}`)
            activeTournament.value = await res.json()
        } catch (err: any) {
            error.value = err.message
        } finally {
            loading.value = false
        }
    }

    async function fetchEntries(tournamentId: number): Promise<void> {
        try {
            const res = await fetch(apiUrl(`/api/predictions/tournaments/${tournamentId}/entries`))
            if (!res.ok) throw new Error(`Failed to load entries: ${res.statusText}`)
            entries.value = await res.json()
        } catch (err: any) {
            error.value = err.message
        }
    }

    async function submitPrediction(tournamentId: number, nickname: string): Promise<void> {
        loading.value = true
        error.value = null
        try {
            const res = await fetch(apiUrl(`/api/predictions/tournaments/${tournamentId}/entries`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nickname: nickname.trim(), picks: myPicks.value }),
            })
            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || `Submission failed: ${res.statusText}`)
            }
            markSubmitted(tournamentId, nickname)
            await fetchEntries(tournamentId)
        } catch (err: any) {
            error.value = err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    function setPick(matchId: string, winner: string, score?: string): void {
        myPicks.value[matchId] = { winner, score: score || undefined }
    }

    function clearPicks(): void {
        myPicks.value = {}
    }

    // ─── Admin actions ──────────────────────────────────────────────────

    async function _adminPost(path: string, body?: object): Promise<any> {
        const authStore = useAuthStore()
        const token = authStore.session?.access_token
        if (!token) throw new Error('Not authenticated')
        const res = await fetch(apiUrl(path), {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : undefined,
        })
        if (!res.ok) {
            const data = await res.json().catch(() => ({}))
            throw new Error(data.detail || `Request failed: ${res.statusText}`)
        }
        return res.json().catch(() => null)
    }

    async function createTournament(managamesUrl: string, closeAt: string): Promise<Tournament> {
        const t = await _adminPost('/api/predictions/tournaments', {
            managames_url: managamesUrl,
            predictions_close_at: closeAt,
        })
        await fetchTournaments()
        return t
    }

    async function refreshResults(tournamentId: number): Promise<void> {
        await _adminPost(`/api/predictions/tournaments/${tournamentId}/refresh`)
        if (activeTournament.value?.id === tournamentId) {
            await fetchTournament(activeTournament.value.slug)
        }
        await fetchEntries(tournamentId)
    }

    async function closePredictions(tournamentId: number): Promise<void> {
        await _adminPost(`/api/predictions/tournaments/${tournamentId}/close`)
        await fetchTournaments()
        if (activeTournament.value?.id === tournamentId) {
            activeTournament.value.status = 'closed'
        }
    }

    async function markFinished(tournamentId: number): Promise<void> {
        await _adminPost(`/api/predictions/tournaments/${tournamentId}/finish`)
        await fetchTournaments()
        if (activeTournament.value?.id === tournamentId) {
            activeTournament.value.status = 'finished'
        }
    }

    async function deleteEntry(entryId: number): Promise<void> {
        const authStore = useAuthStore()
        const token = authStore.session?.access_token
        if (!token) throw new Error('Not authenticated')
        const res = await fetch(apiUrl(`/api/predictions/entries/${entryId}`), {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        })
        if (!res.ok) throw new Error(`Failed to delete entry: ${res.statusText}`)
        entries.value = entries.value.filter(e => e.id !== entryId)
    }

    async function deleteTournament(tournamentId: number): Promise<void> {
        const authStore = useAuthStore()
        const token = authStore.session?.access_token
        if (!token) throw new Error('Not authenticated')
        const res = await fetch(apiUrl(`/api/predictions/tournaments/${tournamentId}`), {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        })
        if (!res.ok) throw new Error(`Failed to delete tournament: ${res.statusText}`)
        await fetchTournaments()
    }

    return {
        tournaments, activeTournament, entries, myPicks, myNickname,
        loading, error, submittedIds,
        hasSubmitted, markSubmitted,
        fetchTournaments, fetchTournament, fetchEntries, submitPrediction,
        setPick, clearPicks,
        createTournament, refreshResults, closePredictions, markFinished,
        deleteEntry, deleteTournament,
    }
})
```

- [ ] **Step 2: Commit**

```bash
cd frontend
git add src/stores/predictions.ts
git commit -m "feat: add predictions Pinia store"
```

---

## Task 6: BracketMatch and BracketEditor components

**Files:**
- Create: `frontend/src/components/predictions/BracketMatch.vue`
- Create: `frontend/src/components/predictions/BracketEditor.vue`

- [ ] **Step 1: Create BracketMatch.vue**

```vue
<!-- frontend/src/components/predictions/BracketMatch.vue -->
<script setup lang="ts">
import type { DrawMatch, PlayerInfo } from '@/stores/predictions'

const props = defineProps<{
    match: DrawMatch
    pickedWinner: string | null
    pickedScore: string | undefined
    readonly: boolean
}>()

const emit = defineEmits<{
    pick: [matchId: string, winner: string, score: string | undefined]
}>()

function selectPlayer(player: PlayerInfo) {
    if (props.readonly || player.name === 'TBD') return
    emit('pick', props.match.id, player.name, props.pickedScore)
}

function onScoreInput(e: Event) {
    const score = (e.target as HTMLInputElement).value
    if (props.pickedWinner) {
        emit('pick', props.match.id, props.pickedWinner, score || undefined)
    }
}

function isSelected(player: PlayerInfo) {
    return props.pickedWinner === player.name
}

function isEliminated(player: PlayerInfo) {
    return props.pickedWinner !== null && props.pickedWinner !== player.name
}

function isActualWinner(player: PlayerInfo) {
    return props.match.winner === player.name
}

function isActualLoser(player: PlayerInfo) {
    return props.match.winner !== null && props.match.winner !== player.name
}

const ROUND_EXACT_PTS: Record<string, number> = {
    R1: 30, R2: 50, R3: 70, QF: 100, SF: 150, F: 200
}
const exactPts = ROUND_EXACT_PTS[props.match.round] ?? 30
</script>

<template>
    <div class="bracket-match">
        <!-- Player 1 -->
        <div
            class="player-row"
            :class="{
                selected: isSelected(match.player1),
                eliminated: isEliminated(match.player1),
                'actual-winner': readonly && isActualWinner(match.player1),
                'actual-loser': readonly && isActualLoser(match.player1),
                tbd: match.player1.name === 'TBD',
                clickable: !readonly && match.player1.name !== 'TBD',
            }"
            @click="selectPlayer(match.player1)"
        >
            <span class="seed">{{ match.player1.seed ? `(${match.player1.seed})` : '' }}</span>
            <span class="name">{{ match.player1.name }}</span>
            <span v-if="isSelected(match.player1)" class="check">✓</span>
        </div>

        <div class="divider" />

        <!-- Player 2 -->
        <div
            class="player-row"
            :class="{
                selected: isSelected(match.player2),
                eliminated: isEliminated(match.player2),
                'actual-winner': readonly && isActualWinner(match.player2),
                'actual-loser': readonly && isActualLoser(match.player2),
                tbd: match.player2.name === 'TBD',
                clickable: !readonly && match.player2.name !== 'TBD',
            }"
            @click="selectPlayer(match.player2)"
        >
            <span class="seed">{{ match.player2.seed ? `(${match.player2.seed})` : '' }}</span>
            <span class="name">{{ match.player2.name }}</span>
            <span v-if="isSelected(match.player2)" class="check">✓</span>
        </div>

        <!-- Score input (shown when a winner is picked and not readonly) -->
        <div v-if="!readonly && pickedWinner" class="score-area">
            <div class="score-label">Score optional · exact = +{{ exactPts }} pts</div>
            <input
                class="score-input"
                type="text"
                :value="pickedScore || ''"
                placeholder="e.g. 6/3 6/2"
                maxlength="20"
                @input="onScoreInput"
            />
        </div>

        <!-- Readonly: show actual score if available -->
        <div v-if="readonly && match.score" class="actual-score">
            {{ match.score }}
        </div>
    </div>
</template>

<style scoped>
.bracket-match {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    min-width: 150px;
    transition: border-color var(--transition-fast);
}
.bracket-match:hover {
    border-color: var(--color-border-hover);
}
.player-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 6px 10px;
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    transition: background var(--transition-fast), color var(--transition-fast);
    min-height: 32px;
}
.player-row.clickable { cursor: pointer; }
.player-row.clickable:hover { background: var(--color-bg-hover); color: var(--color-text-primary); }
.player-row.selected { background: var(--color-accent-light); color: var(--color-accent); font-weight: var(--font-weight-semibold); }
.player-row.eliminated { color: var(--color-text-muted); text-decoration: line-through; }
.player-row.actual-winner { color: var(--color-brand-live); font-weight: var(--font-weight-semibold); }
.player-row.actual-loser { color: var(--color-text-muted); text-decoration: line-through; }
.player-row.tbd { color: var(--color-text-muted); font-style: italic; }
.seed { font-size: var(--font-size-xs); color: var(--color-warning); font-weight: var(--font-weight-bold); min-width: 20px; }
.name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.check { color: var(--color-brand-live); font-size: var(--font-size-sm); }
.divider { height: 1px; background: var(--color-border); }
.score-area { padding: 6px 10px; background: var(--color-bg-secondary); }
.score-label { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-bottom: 3px; }
.score-input {
    width: 100%;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-text-primary);
    font-size: var(--font-size-xs);
    padding: 3px 7px;
    outline: none;
    font-family: var(--font-mono);
}
.score-input:focus { border-color: var(--color-accent); }
.actual-score {
    padding: 4px 10px;
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    background: var(--color-bg-secondary);
}
</style>
```

- [ ] **Step 2: Create BracketEditor.vue**

```vue
<!-- frontend/src/components/predictions/BracketEditor.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import type { DrawData, DrawMatch } from '@/stores/predictions'
import BracketMatch from './BracketMatch.vue'

const props = defineProps<{
    drawData: DrawData
    picks: Record<string, { winner: string; score?: string }>
    readonly: boolean
    section: 'main' | 'qualifying'
}>()

const emit = defineEmits<{
    pick: [matchId: string, winner: string, score: string | undefined]
}>()

// Ordered main draw rounds
const MAIN_ROUNDS = ['R1', 'R2', 'R3', 'QF', 'SF', 'F']
const QUAL_ROUNDS = ['Q1', 'Q2']

const rounds = computed(() =>
    props.section === 'main' ? MAIN_ROUNDS : QUAL_ROUNDS
)

// Group matches by round, filtered to this section
const matchesByRound = computed(() => {
    const sectionMatches = props.drawData.matches.filter(m => m.section === props.section)
    const map: Record<string, DrawMatch[]> = {}
    for (const round of rounds.value) {
        map[round] = sectionMatches.filter(m => m.round === round)
    }
    return map
})

// For R2+ rounds, derive the effective player slots by looking at what
// the user picked in the previous round (or show TBD)
function effectiveMatch(match: DrawMatch, roundIndex: number): DrawMatch {
    if (roundIndex === 0) return match

    const prevRound = rounds.value[roundIndex - 1]
    const prevMatches = matchesByRound.value[prevRound] ?? []

    // This match covers 2^roundIndex players from R1.
    // We derive player1 and player2 from the previous round winner picks.
    const matchIdx = parseInt(match.id.split('_').pop() ?? '0', 10)
    const prevIdx1 = matchIdx * 2
    const prevIdx2 = matchIdx * 2 + 1

    const prev1 = prevMatches[prevIdx1]
    const prev2 = prevMatches[prevIdx2]

    const pick1 = prev1 ? (props.picks[prev1.id]?.winner ?? null) : null
    const pick2 = prev2 ? (props.picks[prev2.id]?.winner ?? null) : null

    return {
        ...match,
        player1: pick1
            ? { name: pick1, seed: null, player_id: null }
            : { name: 'TBD', seed: null, player_id: null },
        player2: pick2
            ? { name: pick2, seed: null, player_id: null }
            : { name: 'TBD', seed: null, player_id: null },
    }
}

const ROUND_LABELS: Record<string, string> = {
    R1: 'R1', R2: 'R2', R3: 'R3', QF: 'QF', SF: 'SF', F: 'F',
    Q1: 'Q1', Q2: 'Q2',
}

const ROUND_PTS: Record<string, string> = {
    R1: '5/30', R2: '10/50', R3: '15/70', QF: '20/100', SF: '30/150', F: '50/200',
    Q1: '—', Q2: '—',
}
</script>

<template>
    <div class="bracket-editor">
        <div
            v-for="(round, roundIndex) in rounds"
            :key="round"
            class="round-col"
        >
            <div class="round-header">
                <span class="round-name">{{ ROUND_LABELS[round] }}</span>
                <span class="round-pts">{{ ROUND_PTS[round] }} pts</span>
            </div>
            <div class="round-matches">
                <div
                    v-for="(match, matchIndex) in matchesByRound[round]"
                    :key="match.id"
                    class="match-wrapper"
                    :style="{ '--depth': roundIndex }"
                >
                    <BracketMatch
                        :match="effectiveMatch(match, roundIndex)"
                        :picked-winner="picks[match.id]?.winner ?? null"
                        :picked-score="picks[match.id]?.score"
                        :readonly="readonly"
                        @pick="(id, w, s) => emit('pick', id, w, s)"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.bracket-editor {
    display: flex;
    gap: 0;
    overflow-x: auto;
    padding-bottom: var(--space-3);
}
.round-col {
    display: flex;
    flex-direction: column;
    min-width: 170px;
    flex-shrink: 0;
}
.round-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-2) var(--space-2);
    border-bottom: 1px solid var(--color-border);
    margin-bottom: var(--space-2);
}
.round-name {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-bold);
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--color-text-secondary);
}
.round-pts {
    font-size: var(--font-size-xs);
    color: var(--color-accent);
    font-weight: var(--font-weight-semibold);
    font-family: var(--font-mono);
}
.round-matches {
    display: flex;
    flex-direction: column;
    flex: 1;
}
.match-wrapper {
    display: flex;
    align-items: center;
    padding: calc(var(--space-1) * (1 + var(--depth, 0))) var(--space-2);
    flex: 1;
}
</style>
```

- [ ] **Step 3: Commit**

```bash
git add src/components/predictions/BracketMatch.vue src/components/predictions/BracketEditor.vue
git commit -m "feat: add BracketMatch and BracketEditor components"
```

---

## Task 7: PredictionLeaderboard component

**Files:**
- Create: `frontend/src/components/predictions/PredictionLeaderboard.vue`

- [ ] **Step 1: Create the component**

```vue
<!-- frontend/src/components/predictions/PredictionLeaderboard.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import type { PredictionEntry, Tournament } from '@/stores/predictions'

const props = defineProps<{
    entries: PredictionEntry[]
    tournament: Tournament
    myNickname: string
}>()

const isFinished = computed(() => props.tournament.status === 'finished')

const maxScore = computed(() => props.entries[0]?.total_score ?? 1)

function barWidth(score: number): string {
    return `${Math.round((score / Math.max(maxScore.value, 1)) * 100)}%`
}

const top3 = computed(() => props.entries.slice(0, 3))
</script>

<template>
    <div class="leaderboard">
        <!-- Podium (only when finished) -->
        <div v-if="isFinished && top3.length" class="podium-wrap">
            <div class="podium-title">Prediction Champions</div>
            <div class="podium">
                <!-- 2nd -->
                <div v-if="top3[1]" class="podium-slot">
                    <div class="avatar silver">{{ top3[1].nickname[0].toUpperCase() }}</div>
                    <div class="podium-name">{{ top3[1].nickname }}</div>
                    <div class="podium-score silver-text">{{ top3[1].total_score }} pts</div>
                    <div class="podium-block silver-block">2</div>
                </div>
                <!-- 1st -->
                <div class="podium-slot">
                    <div class="avatar gold">{{ top3[0].nickname[0].toUpperCase() }}</div>
                    <div class="podium-name">{{ top3[0].nickname }}</div>
                    <div class="podium-score gold-text">{{ top3[0].total_score }} pts</div>
                    <div class="podium-block gold-block">1</div>
                </div>
                <!-- 3rd -->
                <div v-if="top3[2]" class="podium-slot">
                    <div class="avatar bronze">{{ top3[2].nickname[0].toUpperCase() }}</div>
                    <div class="podium-name">{{ top3[2].nickname }}</div>
                    <div class="podium-score bronze-text">{{ top3[2].total_score }} pts</div>
                    <div class="podium-block bronze-block">3</div>
                </div>
            </div>
        </div>

        <!-- Live badge -->
        <div v-if="!isFinished" class="live-badge">
            <span class="live-dot" />
            In progress · scores update when admin refreshes results
        </div>

        <!-- Rankings table -->
        <div v-if="entries.length === 0" class="empty">No predictions yet.</div>
        <div v-else class="rows">
            <div
                v-for="(entry, i) in entries"
                :key="entry.id"
                class="lb-row"
                :class="{
                    'rank-1': i === 0,
                    'is-me': entry.nickname === myNickname,
                }"
            >
                <span class="rank" :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }">
                    {{ i + 1 }}
                </span>
                <span class="nick">
                    {{ entry.nickname }}
                    <span v-if="entry.nickname === myNickname" class="me-tag">YOU</span>
                </span>
                <div class="bar-wrap">
                    <div class="bar" :style="{ width: barWidth(entry.total_score) }" />
                </div>
                <span class="score">{{ entry.total_score }}</span>
            </div>
        </div>
    </div>
</template>

<style scoped>
.leaderboard { display: flex; flex-direction: column; gap: var(--space-4); }

/* Podium */
.podium-title {
    text-align: center; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold);
    text-transform: uppercase; letter-spacing: 1px; color: var(--color-text-secondary);
    margin-bottom: var(--space-4);
}
.podium { display: flex; align-items: flex-end; justify-content: center; gap: var(--space-2); padding-bottom: var(--space-4); border-bottom: 1px solid var(--color-border); }
.podium-slot { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); }
.avatar {
    width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: var(--font-size-base); font-weight: var(--font-weight-bold);
    border: 2px solid;
}
.avatar.gold { background: rgba(245,158,11,0.12); border-color: var(--color-warning); color: var(--color-warning); }
.avatar.silver { background: rgba(148,163,184,0.1); border-color: #94A3B8; color: #94A3B8; }
.avatar.bronze { background: rgba(180,83,9,0.1); border-color: #b45309; color: #b45309; }
.podium-name { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); max-width: 80px; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.podium-score { font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); padding: 2px 7px; border-radius: var(--radius-full); font-family: var(--font-mono); }
.gold-text { color: var(--color-warning); background: rgba(245,158,11,0.12); }
.silver-text { color: #94A3B8; background: rgba(148,163,184,0.08); }
.bronze-text { color: #b45309; background: rgba(180,83,9,0.08); }
.podium-block { border-radius: 6px 6px 0 0; display: flex; align-items: center; justify-content: center; font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-bg-primary); }
.gold-block { width: 84px; height: 90px; background: linear-gradient(160deg, var(--color-warning), #92400e); }
.silver-block { width: 74px; height: 68px; background: linear-gradient(160deg, #94A3B8, #475569); }
.bronze-block { width: 74px; height: 52px; background: linear-gradient(160deg, #b45309, #292524); }

/* Live badge */
.live-badge {
    display: inline-flex; align-items: center; gap: var(--space-2);
    font-size: var(--font-size-xs); color: var(--color-brand-live);
    background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.2);
    padding: var(--space-1) var(--space-3); border-radius: var(--radius-full);
    width: fit-content;
}
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-brand-live); animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

.empty { color: var(--color-text-muted); font-size: var(--font-size-sm); text-align: center; padding: var(--space-8); }

/* Rows */
.rows { display: flex; flex-direction: column; gap: var(--space-2); }
.lb-row {
    display: flex; align-items: center; gap: var(--space-3);
    padding: var(--space-2) var(--space-3);
    background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-md); font-size: var(--font-size-sm);
    transition: border-color var(--transition-fast);
}
.lb-row.rank-1 { border-color: var(--color-warning); background: rgba(245,158,11,0.04); }
.lb-row.is-me { border-color: var(--color-accent); background: var(--color-accent-light); }
.rank { font-weight: var(--font-weight-bold); min-width: 20px; color: var(--color-text-muted); font-size: var(--font-size-xs); }
.rank.gold { color: var(--color-warning); }
.rank.silver { color: #94A3B8; }
.rank.bronze { color: #b45309; }
.nick { flex: 1; color: var(--color-text-primary); font-weight: var(--font-weight-medium); display: flex; align-items: center; gap: var(--space-2); }
.me-tag { font-size: var(--font-size-xs); color: var(--color-accent); border: 1px solid var(--color-accent); padding: 1px 5px; border-radius: var(--radius-sm); font-weight: var(--font-weight-bold); }
.bar-wrap { width: 80px; height: 3px; background: var(--color-border); border-radius: 2px; overflow: hidden; flex-shrink: 0; }
.bar { height: 100%; background: var(--color-accent); border-radius: 2px; }
.lb-row.rank-1 .bar { background: var(--color-warning); }
.score { font-family: var(--font-mono); font-weight: var(--font-weight-bold); color: var(--color-accent); font-size: var(--font-size-sm); min-width: 45px; text-align: right; }
.lb-row.rank-1 .score { color: var(--color-warning); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/predictions/PredictionLeaderboard.vue
git commit -m "feat: add PredictionLeaderboard component with podium"
```

---

## Task 8: AllPredictions and AdminPanel components

**Files:**
- Create: `frontend/src/components/predictions/AllPredictions.vue`
- Create: `frontend/src/components/predictions/AdminPanel.vue`

- [ ] **Step 1: Create AllPredictions.vue**

```vue
<!-- frontend/src/components/predictions/AllPredictions.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { usePredictionsStore, type PredictionEntry, type DrawData } from '@/stores/predictions'
import { useAuthStore } from '@/stores/auth'
import BracketEditor from './BracketEditor.vue'

const props = defineProps<{
    entries: PredictionEntry[]
    drawData: DrawData | null
    tournamentId: number
}>()

const store = usePredictionsStore()
const authStore = useAuthStore()
const viewingEntry = ref<PredictionEntry | null>(null)

function openEntry(entry: PredictionEntry) {
    viewingEntry.value = entry
}
function closeEntry() {
    viewingEntry.value = null
}

async function removeEntry(entry: PredictionEntry) {
    if (!confirm(`Remove prediction by "${entry.nickname}"?`)) return
    try {
        await store.deleteEntry(entry.id)
    } catch (err: any) {
        alert(err.message)
    }
}
</script>

<template>
    <div class="all-predictions">
        <!-- Detail view overlay -->
        <div v-if="viewingEntry" class="detail-overlay">
            <div class="detail-header">
                <button class="back-btn" @click="closeEntry">← Back</button>
                <span class="detail-title">{{ viewingEntry.nickname }}'s Prediction</span>
                <span class="detail-score">{{ viewingEntry.total_score }} pts</span>
            </div>
            <div v-if="drawData" class="detail-bracket">
                <BracketEditor
                    :draw-data="drawData"
                    :picks="viewingEntry.picks"
                    :readonly="true"
                    section="main"
                />
            </div>
        </div>

        <!-- Table -->
        <div v-else>
            <div v-if="entries.length === 0" class="empty">No predictions submitted yet.</div>
            <table v-else class="entries-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Nickname</th>
                        <th>Submitted</th>
                        <th>Score</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="(entry, i) in entries"
                        :key="entry.id"
                        class="entry-row"
                        @click="openEntry(entry)"
                    >
                        <td class="rank-col">{{ i + 1 }}</td>
                        <td class="nick-col">{{ entry.nickname }}</td>
                        <td class="date-col">{{ new Date(entry.submitted_at).toLocaleDateString() }}</td>
                        <td class="score-col">{{ entry.total_score }} pts</td>
                        <td class="actions-col" @click.stop>
                            <button
                                v-if="authStore.isAdmin"
                                class="del-btn"
                                @click="removeEntry(entry)"
                            >✕</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<style scoped>
.all-predictions { display: flex; flex-direction: column; gap: var(--space-3); }
.empty { color: var(--color-text-muted); font-size: var(--font-size-sm); text-align: center; padding: var(--space-8); }

.entries-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.entries-table th { padding: var(--space-2) var(--space-3); text-align: left; font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--color-border); }
.entry-row { cursor: pointer; transition: background var(--transition-fast); }
.entry-row:hover td { background: var(--color-bg-hover); }
.entry-row td { padding: var(--space-3); border-bottom: 1px solid var(--color-border); color: var(--color-text-primary); }
.rank-col { color: var(--color-text-muted); width: 40px; }
.score-col { font-family: var(--font-mono); font-weight: var(--font-weight-bold); color: var(--color-accent); }
.date-col { color: var(--color-text-muted); }
.del-btn { background: none; border: 1px solid var(--color-border); color: var(--color-error); border-radius: var(--radius-sm); padding: 2px 7px; cursor: pointer; font-size: var(--font-size-xs); }
.del-btn:hover { background: var(--color-error-light); border-color: var(--color-error); }

/* Detail overlay */
.detail-overlay { display: flex; flex-direction: column; gap: var(--space-4); }
.detail-header { display: flex; align-items: center; gap: var(--space-4); padding-bottom: var(--space-3); border-bottom: 1px solid var(--color-border); }
.back-btn { background: none; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-1) var(--space-3); color: var(--color-text-secondary); cursor: pointer; font-size: var(--font-size-sm); }
.back-btn:hover { border-color: var(--color-accent); color: var(--color-accent); }
.detail-title { flex: 1; font-weight: var(--font-weight-semibold); color: var(--color-text-primary); }
.detail-score { font-family: var(--font-mono); font-weight: var(--font-weight-bold); color: var(--color-accent); }
.detail-bracket { overflow-x: auto; }
</style>
```

- [ ] **Step 2: Create AdminPanel.vue**

```vue
<!-- frontend/src/components/predictions/AdminPanel.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { usePredictionsStore, type Tournament } from '@/stores/predictions'

const props = defineProps<{
    tournament: Tournament | null
}>()

const emit = defineEmits<{ refresh: [] }>()

const store = usePredictionsStore()
const newUrl = ref('')
const newCloseAt = ref('')
const adminError = ref<string | null>(null)
const adminLoading = ref(false)

async function run(fn: () => Promise<void>) {
    adminLoading.value = true
    adminError.value = null
    try {
        await fn()
        emit('refresh')
    } catch (err: any) {
        adminError.value = err.message
    } finally {
        adminLoading.value = false
    }
}

async function create() {
    if (!newUrl.value || !newCloseAt.value) {
        adminError.value = 'URL and deadline are required'
        return
    }
    await run(() => store.createTournament(newUrl.value, new Date(newCloseAt.value).toISOString()))
    newUrl.value = ''
    newCloseAt.value = ''
}
</script>

<template>
    <div class="admin-panel">
        <div class="admin-header">⚙ Admin Panel</div>

        <div v-if="adminError" class="admin-error">{{ adminError }}</div>

        <!-- Create new tournament -->
        <div class="admin-section">
            <div class="section-title">Add Tournament</div>
            <input
                v-model="newUrl"
                class="admin-input"
                placeholder="https://www.managames.com/Forum/OT_ViewTournament.php?Trn=2045"
            />
            <div class="input-row">
                <input v-model="newCloseAt" class="admin-input" type="datetime-local" />
                <button class="admin-btn primary" :disabled="adminLoading" @click="create">
                    {{ adminLoading ? 'Creating...' : 'Publish Tournament' }}
                </button>
            </div>
        </div>

        <!-- Tournament controls -->
        <div v-if="tournament" class="admin-section">
            <div class="section-title">Manage: {{ tournament.name }}</div>
            <div class="btn-row">
                <button
                    class="admin-btn"
                    :disabled="adminLoading"
                    @click="run(() => store.refreshResults(tournament!.id))"
                >
                    🔄 Refresh Results
                </button>
                <button
                    v-if="tournament.status === 'open'"
                    class="admin-btn warning"
                    :disabled="adminLoading"
                    @click="run(() => store.closePredictions(tournament!.id))"
                >
                    🔒 Close Predictions
                </button>
                <button
                    v-if="tournament.status !== 'finished'"
                    class="admin-btn danger"
                    :disabled="adminLoading"
                    @click="run(() => store.markFinished(tournament!.id))"
                >
                    🏁 Mark Finished
                </button>
                <button
                    class="admin-btn danger"
                    :disabled="adminLoading"
                    @click="run(() => store.deleteTournament(tournament!.id))"
                >
                    🗑 Delete Tournament
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.admin-panel {
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    margin-bottom: var(--space-4);
}
.admin-header { font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: var(--space-3); }
.admin-error { background: var(--color-error-light); border: 1px solid var(--color-error-border); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); color: var(--color-error); font-size: var(--font-size-sm); margin-bottom: var(--space-3); }
.admin-section { margin-bottom: var(--space-4); }
.admin-section:last-child { margin-bottom: 0; }
.section-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary); margin-bottom: var(--space-2); }
.admin-input {
    width: 100%; background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-md); color: var(--color-text-primary); font-size: var(--font-size-sm);
    padding: var(--space-2) var(--space-3); outline: none; margin-bottom: var(--space-2);
}
.admin-input:focus { border-color: var(--color-accent); }
.input-row { display: flex; gap: var(--space-2); }
.input-row .admin-input { margin-bottom: 0; }
.btn-row { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.admin-btn {
    padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium); cursor: pointer; border: 1px solid var(--color-border);
    background: var(--color-surface); color: var(--color-text-primary); transition: all var(--transition-fast);
}
.admin-btn:hover { border-color: var(--color-accent); color: var(--color-accent); }
.admin-btn.primary { background: var(--color-accent); color: var(--color-text-inverse); border-color: var(--color-accent); }
.admin-btn.primary:hover { background: var(--color-accent-hover); }
.admin-btn.warning { border-color: var(--color-warning); color: var(--color-warning); }
.admin-btn.warning:hover { background: var(--color-warning-light); }
.admin-btn.danger { border-color: var(--color-error); color: var(--color-error); }
.admin-btn.danger:hover { background: var(--color-error-light); }
.admin-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add src/components/predictions/AllPredictions.vue src/components/predictions/AdminPanel.vue
git commit -m "feat: add AllPredictions and AdminPanel components"
```

---

## Task 9: PredictionView, router, and XKT tab link

**Files:**
- Create: `frontend/src/views/PredictionView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/OnlineToursView.vue`

- [ ] **Step 1: Create PredictionView.vue**

```vue
<!-- frontend/src/views/PredictionView.vue -->
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { usePredictionsStore } from '@/stores/predictions'
import { useAuthStore } from '@/stores/auth'
import BracketEditor from '@/components/predictions/BracketEditor.vue'
import PredictionLeaderboard from '@/components/predictions/PredictionLeaderboard.vue'
import AllPredictions from '@/components/predictions/AllPredictions.vue'
import AdminPanel from '@/components/predictions/AdminPanel.vue'

const store = usePredictionsStore()
const authStore = useAuthStore()

const activeTab = ref<'prediction' | 'leaderboard' | 'all'>('prediction')
const nicknameInput = ref(store.myNickname)
const submitError = ref<string | null>(null)
const submitSuccess = ref(false)

const tournament = computed(() => {
    // Active = first open or closed tournament; else null
    return store.tournaments.find(t => t.status !== 'finished') ?? null
})

const isOpen = computed(() => tournament.value?.status === 'open')
const isPredictionsClosed = computed(() => (tournament.value?.status ?? '') !== 'open')
const deadlinePassed = computed(() => {
    if (!tournament.value) return false
    return new Date() > new Date(tournament.value.predictions_close_at)
})
const alreadySubmitted = computed(() =>
    tournament.value ? store.hasSubmitted(tournament.value.id) : false
)
const canSubmit = computed(() =>
    isOpen.value && !deadlinePassed.value && !alreadySubmitted.value
)

const pastTournaments = computed(() =>
    store.tournaments.filter(t => t.status === 'finished')
)

onMounted(async () => {
    await store.fetchTournaments()
    if (tournament.value) {
        await Promise.all([
            store.fetchTournament(tournament.value.slug),
            store.fetchEntries(tournament.value.id),
        ])
    }
})

watch(() => tournament.value?.id, async (id) => {
    if (id) {
        await Promise.all([
            store.fetchTournament(tournament.value!.slug),
            store.fetchEntries(id),
        ])
    }
})

async function handleSubmit() {
    submitError.value = null
    const nick = nicknameInput.value.trim()
    if (!nick) { submitError.value = 'Please enter a nickname'; return }
    if (!tournament.value) return
    try {
        await store.submitPrediction(tournament.value.id, nick)
        submitSuccess.value = true
    } catch (err: any) {
        submitError.value = err.message
    }
}

function handlePick(matchId: string, winner: string, score: string | undefined) {
    store.setPick(matchId, winner, score)
}

async function onAdminRefresh() {
    await store.fetchTournaments()
    if (tournament.value) {
        await Promise.all([
            store.fetchTournament(tournament.value.slug),
            store.fetchEntries(tournament.value.id),
        ])
    }
}

function formatDeadline(dt: string) {
    return new Date(dt).toLocaleString(undefined, {
        dateStyle: 'medium', timeStyle: 'short'
    })
}
</script>

<template>
    <div class="prediction-view">
        <div class="page-header">
            <h1>Tournament Predictions</h1>
            <p class="intro">Predict the draw, earn points for exact scores. Top 3 go on the podium.</p>
        </div>

        <!-- Admin panel -->
        <AdminPanel
            v-if="authStore.isAdmin"
            :tournament="store.activeTournament"
            @refresh="onAdminRefresh"
        />

        <!-- Active tournament -->
        <div v-if="store.activeTournament" class="tournament-section">
            <!-- Banner -->
            <div class="tournament-banner">
                <div>
                    <div class="trn-name">{{ store.activeTournament.name }}</div>
                    <div class="trn-meta">
                        {{ store.activeTournament.draw_data?.surface }} ·
                        {{ store.activeTournament.draw_data?.category }} ·
                        Draw {{ store.activeTournament.draw_data?.draw_size }}
                    </div>
                </div>
                <div class="banner-right">
                    <span v-if="isOpen && !deadlinePassed" class="deadline-badge">
                        ⏱ Closes {{ formatDeadline(store.activeTournament.predictions_close_at) }}
                    </span>
                    <span v-else-if="isPredictionsClosed" class="deadline-badge closed">
                        🔒 Predictions closed
                    </span>
                    <span
                        class="status-badge"
                        :class="store.activeTournament.status"
                    >
                        {{ store.activeTournament.status.toUpperCase() }}
                    </span>
                </div>
            </div>

            <!-- Tabs -->
            <div class="tabs">
                <button
                    class="tab"
                    :class="{ active: activeTab === 'prediction' }"
                    @click="activeTab = 'prediction'"
                >🎯 My Prediction</button>
                <button
                    class="tab"
                    :class="{ active: activeTab === 'leaderboard' }"
                    @click="activeTab = 'leaderboard'"
                >🏆 Leaderboard <span class="count">{{ store.entries.length }}</span></button>
                <button
                    class="tab"
                    :class="{ active: activeTab === 'all' }"
                    @click="activeTab = 'all'"
                >📋 All Predictions</button>
            </div>

            <!-- Tab content -->
            <div class="tab-content">

                <!-- My Prediction tab -->
                <div v-if="activeTab === 'prediction'">
                    <div v-if="!store.activeTournament.draw_data?.matches?.length" class="empty">
                        Draw not yet available.
                    </div>
                    <template v-else>
                        <!-- Already submitted -->
                        <div v-if="alreadySubmitted" class="submitted-notice">
                            ✓ You have submitted your prediction for this tournament.
                        </div>

                        <!-- Bracket -->
                        <div class="bracket-section">
                            <h3 class="section-heading">Main Draw</h3>
                            <BracketEditor
                                :draw-data="store.activeTournament.draw_data"
                                :picks="alreadySubmitted ? (store.entries.find(e => e.nickname === store.myNickname)?.picks ?? store.myPicks) : store.myPicks"
                                :readonly="alreadySubmitted || !canSubmit"
                                section="main"
                                @pick="handlePick"
                            />
                        </div>

                        <!-- Submit bar -->
                        <div v-if="canSubmit && !submitSuccess" class="submit-bar">
                            <div v-if="submitError" class="submit-error">{{ submitError }}</div>
                            <div class="submit-row">
                                <input
                                    v-model="nicknameInput"
                                    class="nick-input"
                                    placeholder="Your nickname"
                                    maxlength="30"
                                    @keyup.enter="handleSubmit"
                                />
                                <button
                                    class="submit-btn"
                                    :disabled="store.loading"
                                    @click="handleSubmit"
                                >
                                    {{ store.loading ? 'Submitting...' : 'Submit Prediction →' }}
                                </button>
                            </div>
                            <div class="submit-hint">One submission per IP. Cannot be changed after submit.</div>
                        </div>

                        <div v-if="submitSuccess" class="success-notice">
                            🎉 Prediction submitted! Check the leaderboard tab.
                        </div>
                    </template>
                </div>

                <!-- Leaderboard tab -->
                <div v-if="activeTab === 'leaderboard'">
                    <PredictionLeaderboard
                        :entries="store.entries"
                        :tournament="store.activeTournament"
                        :my-nickname="store.myNickname"
                    />
                </div>

                <!-- All predictions tab -->
                <div v-if="activeTab === 'all'">
                    <AllPredictions
                        :entries="store.entries"
                        :draw-data="store.activeTournament.draw_data ?? null"
                        :tournament-id="store.activeTournament.id"
                    />
                </div>
            </div>
        </div>

        <!-- No active tournament -->
        <div v-else-if="!store.loading" class="no-tournament">
            <p>No active tournament at the moment. Check the archive below.</p>
        </div>

        <!-- Archive -->
        <div v-if="pastTournaments.length" class="archive-section">
            <h2 class="archive-title">Past Tournaments</h2>
            <div class="archive-grid">
                <div
                    v-for="t in pastTournaments"
                    :key="t.id"
                    class="archive-card"
                >
                    <div class="archive-name">{{ t.name }}</div>
                    <div class="archive-meta">{{ new Date(t.created_at).getFullYear() }}</div>
                    <div class="archive-entries">{{ t.entry_count }} predictions</div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.prediction-view { min-height: 100%; display: flex; flex-direction: column; gap: var(--space-6); }
.page-header h1 { font-size: var(--font-size-3xl); font-weight: var(--font-weight-bold); color: var(--color-text-primary); margin-bottom: var(--space-2); }
.intro { color: var(--color-text-secondary); font-size: var(--font-size-base); }

/* Banner */
.tournament-banner {
    display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: var(--space-3);
    background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-lg); padding: var(--space-4) var(--space-5);
    margin-bottom: var(--space-4);
}
.trn-name { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }
.trn-meta { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: var(--space-1); }
.banner-right { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.deadline-badge { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-warning); background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); padding: var(--space-1) var(--space-3); border-radius: var(--radius-full); }
.deadline-badge.closed { color: var(--color-text-muted); background: var(--color-bg-secondary); border-color: var(--color-border); }
.status-badge { font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); padding: var(--space-1) var(--space-3); border-radius: var(--radius-full); text-transform: uppercase; letter-spacing: 0.5px; }
.status-badge.open { background: rgba(34,197,94,0.1); color: var(--color-brand-live); border: 1px solid rgba(34,197,94,0.2); }
.status-badge.closed { background: var(--color-bg-secondary); color: var(--color-text-muted); border: 1px solid var(--color-border); }
.status-badge.finished { background: rgba(245,158,11,0.1); color: var(--color-warning); border: 1px solid rgba(245,158,11,0.3); }

/* Tabs */
.tabs { display: flex; gap: var(--space-1); border-bottom: 2px solid var(--color-border); padding-bottom: 0; margin-bottom: var(--space-4); }
.tab { padding: var(--space-2) var(--space-4); font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-text-secondary); background: transparent; border: none; border-bottom: 2px solid transparent; cursor: pointer; margin-bottom: -2px; transition: all var(--transition-fast); display: flex; align-items: center; gap: var(--space-2); }
.tab:hover { color: var(--color-text-primary); }
.tab.active { color: var(--color-accent); border-bottom-color: var(--color-accent); }
.count { font-size: var(--font-size-xs); background: var(--color-bg-secondary); padding: 1px 6px; border-radius: var(--radius-full); color: var(--color-text-muted); }

.tab-content { animation: fadeIn 0.15s ease-out; }
@keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:none} }

/* Bracket */
.bracket-section { overflow-x: auto; margin-bottom: var(--space-4); }
.section-heading { font-size: var(--font-size-base); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary); margin-bottom: var(--space-3); }

/* Submit bar */
.submit-bar { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-4); margin-top: var(--space-4); }
.submit-error { background: var(--color-error-light); border: 1px solid var(--color-error-border); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); color: var(--color-error); font-size: var(--font-size-sm); margin-bottom: var(--space-3); }
.submit-row { display: flex; gap: var(--space-3); align-items: center; }
.nick-input { flex: 1; background: var(--color-bg-secondary); border: 1px solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text-primary); font-size: var(--font-size-sm); padding: var(--space-2) var(--space-3); outline: none; }
.nick-input:focus { border-color: var(--color-accent); }
.submit-btn { background: var(--color-accent); color: var(--color-text-inverse); font-weight: var(--font-weight-bold); font-size: var(--font-size-sm); padding: var(--space-2) var(--space-5); border-radius: var(--radius-md); border: none; cursor: pointer; white-space: nowrap; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.submit-hint { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: var(--space-2); }

/* Notices */
.submitted-notice, .success-notice {
    background: var(--color-success-light); border: 1px solid var(--color-success-border);
    border-radius: var(--radius-md); padding: var(--space-3) var(--space-4);
    color: var(--color-success); font-size: var(--font-size-sm); margin-bottom: var(--space-4);
}
.no-tournament { color: var(--color-text-muted); font-size: var(--font-size-sm); padding: var(--space-6) 0; }
.empty { color: var(--color-text-muted); font-size: var(--font-size-sm); text-align: center; padding: var(--space-8); }

/* Archive */
.archive-section { padding-top: var(--space-6); border-top: 1px solid var(--color-border); }
.archive-title { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-text-primary); margin-bottom: var(--space-4); }
.archive-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-3); }
.archive-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-4); transition: border-color var(--transition-fast); }
.archive-card:hover { border-color: var(--color-accent); }
.archive-name { font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin-bottom: var(--space-1); }
.archive-meta { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.archive-entries { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: var(--space-2); }
</style>
```

- [ ] **Step 2: Add route to router**

Open `frontend/src/router/index.ts`. Inside the `children` array of `/online-tours`, add after the `wtsl` child:

```typescript
// Add this import at the top of router/index.ts
const PredictionView = () => import('../views/PredictionView.vue')

// Add inside the children array of the /online-tours route, after the wtsl entry:
{
    path: 'xkt/predictions',
    name: 'XKTPredictions',
    component: PredictionView,
    meta: {
        title: 'XKT Tournament Predictions',
        description: 'Predict XKT tournament bracket results and compete with other players.'
    }
}
```

- [ ] **Step 3: Add predictions card to XKT tab in OnlineToursView.vue**

In `frontend/src/views/OnlineToursView.vue`, add this import at the top of `<script setup>`:

```typescript
import { Trophy } from 'lucide-vue-next'
```

Then find the closing `</div>` of the `.tour-links` section (after the WTSL `tour-stats-section` block) and add before `<!-- Guide Video Link -->`:

```html
<!-- Tournament Predictions Link (XKT only) -->
<div v-if="currentTourKey === 'xkt'" class="tour-stats-section">
    <h3>Tournament Predictions</h3>
    <RouterLink
        to="/online-tours/xkt/predictions"
        class="link-card tour-predictions-highlight"
    >
        <span class="link-icon-wrapper mod-predictions">
            <Trophy :size="24" stroke-width="2.5" />
        </span>
        <div class="tour-logs-content">
            <span class="link-label">Predict the Draw</span>
            <span class="link-sublabel">Pick match winners, score exact results, win the podium</span>
        </div>
        <span class="link-arrow">→</span>
    </RouterLink>
</div>
```

Add the CSS for `.tour-predictions-highlight` and `.mod-predictions` at the end of the `<style scoped>` block:

```css
.tour-predictions-highlight {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.05));
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: var(--space-5);
}
.tour-predictions-highlight:hover {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.1));
    border-color: var(--color-warning);
}
.mod-predictions { color: var(--color-warning); background: rgba(245, 158, 11, 0.1); }
```

- [ ] **Step 4: Start the dev servers and verify**

Terminal 1 (backend):
```bash
cd backend
uvicorn app.main:app --reload
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173/online-tours/xkt` — you should see the "Tournament Predictions" card.  
Open `http://localhost:5173/online-tours/xkt/predictions` — the view should load (showing "No active tournament" if none exist).  
Log in as admin, paste a managames URL, publish a tournament, and verify the bracket appears.

- [ ] **Step 5: Commit**

```bash
git add src/views/PredictionView.vue src/router/index.ts src/views/OnlineToursView.vue
git add src/components/predictions/
git commit -m "feat: add PredictionView, router route, and XKT tab card"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Route `/online-tours/xkt/predictions` — Task 9
- ✅ PredictionTournament + PredictionEntry models — Task 1
- ✅ Scoring engine (all round points, exact/sets/partial) — Task 2
- ✅ Tournament draw scraper (managames HTML) — Task 3
- ✅ All 9 API endpoints — Task 4
- ✅ IP + nickname uniqueness lock — Task 4 (endpoint)
- ✅ localStorage submission token — Task 5 (store)
- ✅ Bracket editor (left-to-right, TBD propagation) — Task 6
- ✅ Score input with points hint — Task 6 (BracketMatch)
- ✅ Live leaderboard — Task 7
- ✅ Podium (gold/silver/bronze) — Task 7
- ✅ All Predictions tab with entry viewer — Task 8
- ✅ Admin panel (create, refresh, close, finish, delete) — Task 8
- ✅ Historical archive grid — Task 9 (PredictionView)
- ✅ XKT tab card — Task 9
- ✅ Admin delete entry — Task 8 (AllPredictions) + Task 4 (endpoint)

**Type consistency check:**
- `DrawMatch`, `PlayerInfo`, `Tournament`, `PredictionEntry` defined in store (Task 5) and imported in all components ✅
- `compute_entry_score(picks, matches)` called in Task 4 (refresh endpoint) matches signature defined in Task 2 ✅
- `scrape_tournament_draw(url)` called in Task 4 matches signature defined in Task 3 ✅
- `store.activeTournament` used in PredictionView — populated by `fetchTournament(slug)` in Task 5 ✅
- `store.myPicks` keyed by `match.id` — same key format used in BracketEditor and scoring engine ✅
