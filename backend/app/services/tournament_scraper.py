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

import asyncio
import http.client
import re
import socket
import ssl
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger

logger = get_logger("tournament_scraper")

# Maps abbreviated column headers to canonical round names
_ROUND_MAP: dict[str, str] = {
    "Q1": "Q1", "Q2": "Q2", "Q3": "Q3", "Q4": "Q4", "Q5": "Q5", "Q6": "Q6",
    "Qualified": "Qualified",
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


_TBD: dict = {"name": "TBD", "seed": None, "player_id": None}


def _parse_player_cell(td: Tag) -> dict:
    """Extract player info from a draw table <td> cell.

    Returns dict with keys: name, seed, player_id.
    Returns _TBD for empty/unplayed cells.
    """
    if td is None:
        return _TBD

    # Named player with link
    link = td.find("a", href=re.compile(r"OT_Player\.php"))
    if link:
        name = link.get_text(strip=True)
        href = link.get("href", "")
        pid_match = re.search(r"p=(\d+)", href)
        player_id = pid_match.group(1) if pid_match else None
        full_text = td.get_text()
        seed_match = re.search(r"\((\d+)\)", full_text)
        seed = int(seed_match.group(1)) if seed_match else None
        return {"name": name, "seed": seed, "player_id": player_id}

    # Plain text: strip score span content first, then use remaining text
    # (e.g. "Qualifier #2", "Lucky Loser", "Bye")
    text = td.get_text(strip=True)
    score_span = td.find("span", class_="score")
    if score_span:
        text = text.replace(score_span.get_text(strip=True), "").strip()

    if not text or text in ("TBD", "Bye"):
        return _TBD

    return {"name": text, "seed": None, "player_id": None}


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


def _collect_col_cells(data_rows: list, col_idx: int) -> list[Tag]:
    """Return ordered list of unique (non-rowspan-continuation) tds for a column."""
    cells: list[Tag] = []
    seen: set[int] = set()
    for row_idx, row in enumerate(data_rows):
        if col_idx >= len(row):
            continue
        cell = row[col_idx]
        if cell is None or row_idx in seen:
            continue
        rs = cell["rowspan"]
        seen.update(range(row_idx, min(row_idx + rs, len(data_rows))))
        cells.append(cell["td"])
    return cells


def _parse_draw_table(table: Tag, section: str) -> list[dict]:
    """Parse one draw table (main or qualifying) into a list of match dicts.

    Column semantics:
      Col 0  — individual player slots (R1 entries)
      Col N  — result of match between the two col N-1 cells this cell spans
               → contains winner name + score (empty if not played yet)

    Match round names come from col N-1 header (the round being played).
    Handles variable draw sizes (R1,R2,Q,S,F,W or R1,R2,R3,Q,S,F,W etc.).
    """
    thead = table.find("thead")
    if not thead:
        return []

    headers = [th.get_text(strip=True) for th in thead.find_all("th", class_="Large")]
    rounds = [_ROUND_MAP.get(h) for h in headers]  # None for unknown, "W" for winner col

    grid = _build_virtual_grid(table)

    # Drop points/date header rows — keep only rows with actual player/result cells
    data_rows = []
    for row in grid:
        for cell in row:
            if cell and cell["td"]:
                cls = cell["td"].get("class") or []
                if "Points" not in cls and "Hidden" not in cls:
                    data_rows.append(row)
                    break

    # Build ordered cell list per column
    num_cols = len(rounds)
    col_cells = [_collect_col_cells(data_rows, c) for c in range(num_cols)]

    matches: list[dict] = []

    # Iterate player columns (col 0 .. num_cols-2); col N+1 holds the result.
    # Skip col whose round is None or "W" (winner display only).
    for col_idx in range(num_cols - 1):
        round_name = rounds[col_idx]
        if not round_name or round_name == "W":
            continue

        player_cells = col_cells[col_idx]
        result_cells = col_cells[col_idx + 1] if col_idx + 1 < num_cols else []

        # Pair up cells two-by-two — each pair = one match
        for match_i, i in enumerate(range(0, len(player_cells) - 1, 2)):
            p1 = _parse_player_cell(player_cells[i])
            p2 = _parse_player_cell(player_cells[i + 1])

            winner_name: str | None = None
            score: str | None = None
            if match_i < len(result_cells):
                result_td = result_cells[match_i]
                result_player = _parse_player_cell(result_td)
                if result_player["name"] != "TBD":
                    winner_name = result_player["name"]
                    score = _parse_score_cell(result_td)

            matches.append({
                "id": f"{section}_{round_name}_{match_i}",
                "section": section,
                "round": round_name,
                "player1": p1,
                "player2": p2,
                "winner": winner_name,
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
        urllib.error.URLError: If the page cannot be fetched.
        ValueError: If the page structure is unexpected.
    """
    _req_headers = {
        "User-Agent": "TennisTracker/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "identity",
        "Referer": "http://www.managames.com/",
        "Upgrade-Insecure-Requests": "1",
        # managames serves a JS cookie-challenge page to cookieless clients.
        # Browsers execute the JS, set __passedJS=1, and reload. We simulate that.
        "Cookie": "__passedJS=1",
    }

    def _fetch_html() -> str:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")

        # Force IPv4: many servers (including Render) have no IPv6 routing.
        _orig_getaddrinfo = socket.getaddrinfo

        def _ipv4_only(*args, **kwargs):
            """Override to force AF_INET (IPv4) resolution."""
            return _orig_getaddrinfo(args[0], args[1], socket.AF_INET, *args[3:], **kwargs)

        logger.info("Connecting to %s port %d", hostname, port)
        try:
            socket.getaddrinfo = _ipv4_only
            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(hostname, port, context=ctx, timeout=30)

            conn.request("GET", path, headers=_req_headers)
            resp = conn.getresponse()
            logger.info("HTTP %d for %s", resp.status, url)
            if resp.status >= 400:
                raise OSError(f"HTTP {resp.status} {resp.reason}")
            raw = resp.read()
            conn.close()
        except Exception as exc:
            logger.error("Fetch failed for %s: %s: %s", url, type(exc).__name__, exc)
            raise
        finally:
            socket.getaddrinfo = _orig_getaddrinfo
        return raw.decode("utf-8", errors="replace")

    html = await asyncio.to_thread(_fetch_html)

    logger.info("Fetched %s — %d bytes", url, len(html))
    if len(html) < 1000:
        logger.warning("Tiny response body: %r", html)

    soup = BeautifulSoup(html, "lxml")

    # Debug: log key structural elements
    h2 = soup.find("h2")
    logger.info("h2 text: %r", h2.get_text()[:120] if h2 else None)
    dt_labels = [dt.get_text(strip=True) for dt in soup.find_all("dt")]
    logger.info("dt labels found: %r", dt_labels)
    ot_tables = soup.find_all("table", class_="Ot")
    logger.info("tables.Ot count: %d", len(ot_tables))
    scrollable = soup.find_all("div", class_="OtScrollableContainer")
    logger.info("OtScrollableContainer divs: %d", len(scrollable))

    meta = _parse_tournament_meta(soup)
    logger.info("Parsed meta: %s", meta)

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
                    section_matches = _parse_draw_table(table, "main")
                    logger.info("Main draw table → %d matches", len(section_matches))
                    all_matches.extend(section_matches)
        elif label == "Qualifications":
            parent_dl = dt.parent
            table = parent_dl.find("table", class_="Ot")
            if table:
                section_matches = _parse_draw_table(table, "qualifying")
                logger.info("Qualifying table → %d matches", len(section_matches))
                all_matches.extend(section_matches)

    logger.info("Total matches parsed: %d", len(all_matches))

    return {
        "name": meta["name"],
        "surface": meta["surface"],
        "category": meta["category"],
        "draw_size": meta["draw_size"],
        "week": meta["week"],
        "year": meta["year"],
        "matches": all_matches,
    }
