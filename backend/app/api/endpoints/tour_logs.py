"""WTSL Tour Logs API endpoints.

Fetches and processes tour log data from Google Sheets CSV.
"""

import asyncio
import csv
import hashlib
import re
import time
from datetime import date, timedelta
from io import StringIO
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from app.core.limiter import limiter
from app.core.logging import get_logger

logger = get_logger("api.tour_logs")
router = APIRouter(prefix="/tour-logs", tags=["Tour Logs"])

# In-memory cache: every request used to refetch+reparse all 3 Google Sheets from
# scratch, so concurrent traffic (or a client re-requesting different pages) meant
# many redundant outbound calls to Google - slow, and prone to 502s if Google is
# briefly slow to answer. Single systemd process on the VPS, so a module-level
# cache is safe (see project memory: no cross-instance fragmentation risk here).
_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
CACHE_TTL_SECONDS = 120

# Google Sheets publish token - one doc, three tabs (atp/wta/dubs), each with its own gid
TOUR_LOGS_PUB_BASE = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vRm0Kujb49DJx1yWV8rE_DRXKBuTEc24jIOHjPpjaZd2OVIESYohFtbGCEJGDhtxIxXtpIM_8YnMeaP"
    "/pub"
)
TOUR_SHEET_GIDS = {
    "atp": "1587269725",
    "wta": "1691157729",
    "dubs": "1805994776",
}


def sheet_csv_url(gid: str) -> str:
    """Build the CSV export URL for one tab of the published sheet."""
    return f"{TOUR_LOGS_PUB_BASE}?gid={gid}&single=true&output=csv"


def is_valid_result(result: str) -> bool:
    """Filter out invalid result entries.
    
    Args:
        result: The result string from CSV.
        
    Returns:
        True if valid match result, False otherwise.
    """
    if not result or not result.strip():
        return False
    
    result_lower = result.lower().strip()
    
    # Exclude these patterns
    exclude_patterns = ['result', 'resultsx', 'zak']
    if any(ex in result_lower for ex in exclude_patterns):
        return False
    
    # Exclude date patterns (e.g., "07-may.", "12-jan")
    if re.match(r'^\d{1,2}-[a-z]{3}', result_lower):
        return False
    
    # Keep retirements (contains "ret")
    if 'ret' in result_lower:
        return True
    # Valid formats:
    # - "6/4 6/3" (slash separated)
    # - "60 61" or "60 60 60" (two digits = 6-0, 6-1 format)
    # - "76(2) 64" (tiebreak format)
    # - "6-4 7-6(3)" (dash separated, new export format)
    if re.match(r'^[0-9]/[0-9]', result):
        return True
    if re.match(r'^\d{2}(\(\d+\))?(\s|$)', result):  # e.g., "60 " or "76(2) "
        return True
    if re.match(r'^\d{1,2}-\d{1,2}(\(\d+\))?(\s|$)', result):  # e.g., "6-4 " or "7-6(3) "
        return True

    return False


def clean_date(date_str: str) -> str:
    """Remove time from date string, converting raw spreadsheet serial dates too.

    Args:
        date_str: Date string like "17/01/2024 19:56", or a raw Excel/Sheets
            serial date like "45901" or "45751,94583" (unformatted cell).

    Returns:
        Date only, as "DD/MM/YYYY".
    """
    if not date_str:
        return ""
    date_str = date_str.strip()
    if '/' in date_str:
        # Already a formatted date, just drop any time component
        return date_str.split()[0] if ' ' in date_str else date_str

    # Raw serial date (wta/dubs sheets export unformatted date cells), e.g. "45901"
    # or "45751,94583" (integer day + fractional time-of-day, comma decimal).
    serial_str = date_str.replace(',', '.')
    if re.match(r'^\d+(\.\d+)?$', serial_str):
        try:
            serial_days = int(float(serial_str))
            # Sheets/Excel serial epoch is 1899-12-30 (includes the historical leap-year bug)
            converted = date(1899, 12, 30) + timedelta(days=serial_days)
            return converted.strftime('%d/%m/%Y')
        except (ValueError, OverflowError):
            return date_str
    return date_str


def parse_elo(elo_str: str) -> int | None:
    """Extract numeric ELO from string.
    
    Args:
        elo_str: ELO string like "1870" or "NaN"
        
    Returns:
        ELO value or None.
    """
    if not elo_str or str(elo_str).lower() == 'nan':
        return None
    try:
        # Take first part if there's a space (though new format seems to be just number)
        return int(str(elo_str).split()[0])
    except (ValueError, IndexError):
        return None


def parse_percentage(pct_str: str) -> float | None:
    """Parse percentage string to float (0-100 scale).

    Args:
        pct_str: Percentage like "86%" (atp/wta-formatted) or a raw fraction
            like "0,86" (wta/dubs unformatted cell, comma decimal) or "NaN".

    Returns:
        Float value 0-100, or None if invalid.
    """
    if not pct_str or str(pct_str).lower() == 'nan':
        return None
    raw = str(pct_str).strip()
    has_percent_sign = '%' in raw
    normalized = raw.replace('%', '').replace(',', '.').strip()
    try:
        value = float(normalized)
    except ValueError:
        return None
    # Unformatted cells store the raw 0-1 fraction instead of "NN%"
    if not has_percent_sign and 0 <= value <= 1:
        value *= 100
    return value


def parse_number(num_str: str) -> float | None:
    """Parse numeric string to float.

    Args:
        num_str: Number like "5.8" or "5,8" (comma-decimal, unformatted cell) or "NaN".

    Returns:
        Float value or None if invalid.
    """
    if not num_str or str(num_str).lower() == 'nan':
        return None
    try:
        return float(str(num_str).strip().replace(',', '.'))
    except ValueError:
        return None


def sanitize_for_csv(value: str) -> str:
    """Sanitize string to prevent CSV formula injection."""
    if not value:
        return ""
    
    value = str(value).strip()
    if value and value[0] in ('=', '+', '-', '@'):
        return f"'{value}"
    return value


def generate_ids(row: dict[str, Any]) -> tuple[str, str]:
    """Generate unique IDs for the row and the match.
    
    Returns:
        (row_id, match_id)
    """
    # Key components
    date = row.get('dateTime', '')
    image = row.get('imageName', '')
    tournament = row.get('tournament', '')
    p1 = row.get('player', '').lower().strip()
    p2 = row.get('opponent', '').lower().strip()
    
    # Match ID: Unique to the match event (same for both players)
    # Sort players to ensure commutativity
    players_sorted = sorted([p1, p2])
    match_str = f"{date}|{tournament}|{image}|{players_sorted[0]}|{players_sorted[1]}"
    match_id = hashlib.sha256(match_str.encode()).hexdigest()
    
    # Row ID: Unique to this specific player stat entry
    row_str = f"{match_id}|{p1}"
    row_id = hashlib.sha256(row_str.encode()).hexdigest()
    
    return row_id, match_id


def process_row(row: dict[str, str], tour: str) -> dict[str, Any] | None:
    """Process a single CSV row into cleaned data.

    Args:
        row: Raw CSV row as dictionary.
        tour: Which tab the row came from ("atp", "wta", or "dubs").

    Returns:
        Cleaned row data or None if invalid.
    """
    result = row.get('Result', '')
    if not is_valid_result(result):
        return None

    # Basic fields
    raw_date = row.get('Date', '').strip()
    # Dubs sheet: "Player" is just one team member; "Dubs team" has the full pairing
    # (e.g. "Arv & John McEnroe") which matches how the "Opponent" column already reads.
    raw_player = row.get('Dubs team', '').strip() or row.get('Player', '')
    player_name = sanitize_for_csv(raw_player)
    opponent_name = sanitize_for_csv(row.get('Opponent', ''))
    match_image = sanitize_for_csv(row.get('Image Name', ''))
    tournament = sanitize_for_csv(row.get('Tournament', ''))
    
    # Temporary dict to generate IDs
    temp_data = {
        'dateTime': raw_date,
        'imageName': match_image,
        'tournament': tournament,
        'player': player_name,
        'opponent': opponent_name
    }
    
    row_id, match_id = generate_ids(temp_data)

    # Sheet-provided match key (Player+Opponent+Tournament+Date concatenation).
    # More reliable than our own match_id hash for grouping duplicate rows of
    # the same match, since Image Name (part of match_id) is often misnumbered
    # and differs between rows that are really the same match.
    unique_id = row.get('Unique ID B', '').strip() or match_id

    return {
        'id': row_id,
        'matchId': match_id,
        'uniqueId': unique_id,
        'tour': tour,
        'imageName': match_image,
        'player': player_name,
        'elo': parse_elo(row.get('ELO', '')),
        'crc': row.get('Crc', '').strip(),
        'result': result.strip(),
        'opponent': opponent_name,
        'opponentElo': parse_elo(row.get('Opponent ELO', '')),
        'opponentCrc': row.get('Opponent Crc', '').strip(),
        'tournament': tournament,
        'dateTime': raw_date,
        'date': clean_date(raw_date),
        # Stats - Serve
        'firstServePct': parse_percentage(row.get('1st Serve %', '')),
        'aces': parse_number(row.get('Aces', '')),
        'doubleFaults': parse_number(row.get('Double Faults', '')),
        'fastestServe': parse_number(row.get('Fastest Serve', '')),
        'avgFirstServeSpeed': parse_number(row.get('Avg 1st Serve Speed', '')),
        'avgSecondServeSpeed': parse_number(row.get('Avg 2nd Serve Speed', '')),
        # Stats - Points
        'winners': parse_number(row.get('Winners', '')),
        'forcedErrors': parse_number(row.get('Forced Errors', '')),
        'unforcedErrors': parse_number(row.get('Unforced Errors', '')),
        'totalPointsWon': parse_number(row.get('Total Points Won', '')),
        # Stats - Net/Return
        'netPointsWonPct': parse_percentage(row.get('Net Points Won %', '')),
        'returnPointsWonPct': parse_percentage(row.get('Return Points Won %', '')),
        'returnWinners': parse_number(row.get('Return Winners', '')),
        # Stats - Break Points
        'breakPointsWonPct': parse_percentage(row.get('Break Points Won %', '')),
        'breaksPerGamePct': parse_percentage(row.get('Breaks / Games %', '')),
        'setPointsSaved': parse_number(row.get('Set Points Saved', '')),
        'matchPointsSaved': parse_number(row.get('Match Points Saved', '')),
        # Stats - Rally
        'shortRalliesWonPct': parse_percentage(row.get('Short Rallies Won (<5) %', '')),
        'mediumRalliesWonPct': parse_percentage(row.get('Medium Rallies Won (5-8) %', '')),
        'longRalliesWonPct': parse_percentage(row.get('Long Rallies Won (>8) %', '')),
        'avgRallyLength': parse_number(row.get('Average Rally Length', '')),
        # Stats - Serve Won
        'firstServeWonPct': parse_percentage(row.get('1st Serve Won %', '')),
        'secondServeWonPct': parse_percentage(row.get('2nd Serve Won %', '')),
    }


async def fetch_and_process_all_sheets() -> list[dict[str, Any]]:
    """Fetch all 3 tabs (atp/wta/dubs) from Google Sheets and return processed rows."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        responses = await asyncio.gather(
            *[client.get(sheet_csv_url(gid)) for gid in TOUR_SHEET_GIDS.values()]
        )
    for response in responses:
        response.raise_for_status()

    # Process all valid rows from every tab (atp/wta/dubs), tagged by tour
    processed_data = []
    for tour, response in zip(TOUR_SHEET_GIDS.keys(), responses):
        content = response.content.decode('latin-1')

        # Check first line to see if headers are present
        params = {}
        first_line = content.splitlines()[0] if content else ""
        if "Result" not in first_line and "Player" not in first_line:
             # Assume headers are missing, provide default list based on observed structure
             # Critical columns: 0=Image, 1=Player, 4=Result, 5=Opponent, 8=Tournament, 9=Date
             params['fieldnames'] = [
                 "Image Name", "Player", "ELO", "Crc", "Result", "Opponent",
                 "Opponent ELO", "Opponent Crc", "Tournament", "Date",
                 "1st Serve %", "Aces", "Double Faults", "Fastest Serve",
                 "Avg 1st Serve Speed", "Avg 2nd Serve Speed", "Winners",
                 "Forced Errors", "Unforced Errors", "Net Points Won %",
                 "Return Points Won %", "Total Points Won", "Break Points Won %",
                 "Breaks / Games %", "Set Points Saved",
                 "Average Rally Length", "1st Serve Won %", "2nd Serve Won %",
                 "Return Winners"
             ]
             logger.warning(f"CSV headers missing for '{tour}' sheet, using hardcoded fieldnames")

        reader = csv.DictReader(StringIO(content), **params)
        for row in reader:
            processed = process_row(row, tour)
            if processed:
                processed_data.append(processed)

    return processed_data


async def get_cached_tour_logs() -> list[dict[str, Any]]:
    """Return processed tour log rows, refetching from Google Sheets only every
    CACHE_TTL_SECONDS instead of on every request."""
    now = time.monotonic()
    if _cache["data"] is None or (now - _cache["fetched_at"]) >= CACHE_TTL_SECONDS:
        _cache["data"] = await fetch_and_process_all_sheets()
        _cache["fetched_at"] = now
    return _cache["data"]


@router.get(
    "",
    summary="Get tour logs data",
    description="Fetch and return cleaned tour log data from Google Sheets.",
)
@limiter.limit("20/minute")
async def get_tour_logs(
    request: Request,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    # Frontend fetches the whole (atp+wta+dubs) dataset in one call to aggregate
    # client-side (leaderboards, filters) - le=10000 covers that in a single page
    # instead of needing dozens of requests against the 20/minute limit below.
    page_size: Annotated[int, Query(ge=1, le=10000, description="Results per page")] = 50,
) -> dict[str, Any]:
    """Fetch tour logs from Google Sheets (cached) and return paginated cleaned data.

    Returns:
        Dictionary with success status, pagination info, and data array.
    """
    try:
        processed_data = await get_cached_tour_logs()

        total = len(processed_data)
        start = (page - 1) * page_size
        paginated = processed_data[start : start + page_size]

        logger.info(f"Fetched {total} tour log entries, returning page {page}")

        return {
            "success": True,
            "count": len(paginated),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),  # ceiling division
            "data": paginated,
        }

    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch tour logs: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch tour logs data")
    except Exception as e:
        logger.error(f"Error processing tour logs: {e}")
        raise HTTPException(status_code=500, detail="Error processing tour logs data")
