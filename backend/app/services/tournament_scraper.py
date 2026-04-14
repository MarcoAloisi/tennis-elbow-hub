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
