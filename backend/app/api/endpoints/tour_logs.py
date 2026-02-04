"""WTSL Tour Logs API endpoints.

Fetches and processes tour log data from Google Sheets CSV.
"""

import hashlib
import re
from io import StringIO
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.core.limiter import limiter
from app.core.logging import get_logger

logger = get_logger("api.tour_logs")
router = APIRouter(prefix="/tour-logs", tags=["Tour Logs"])

# Google Sheets published CSV URL
TOUR_LOGS_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vRm0Kujb49DJx1yWV8rE_DRXKBuTEc24jIOHjPpjaZd2OVIESYohFtbGCEJGDhtxIxXtpIM_8YnMeaP"
    "/pub?output=csv"
)


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
    if re.match(r'^[0-9]/[0-9]', result):
        return True
    if re.match(r'^\d{2}(\(\d+\))?(\s|$)', result):  # e.g., "60 " or "76(2) "
        return True
    
    return False


def clean_date(date_str: str) -> str:
    """Remove time from date string.
    
    Args:
        date_str: Date string like "17/01/2024 19:56"
        
    Returns:
        Date only: "17/01/2024"
    """
    if not date_str:
        return ""
    # Usually format is M/D/YYYY H:MM:SS or similar
    return date_str.split()[0] if ' ' in date_str else date_str


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
    """Parse percentage string to float.
    
    Args:
        pct_str: Percentage like "86%" or "NaN"
        
    Returns:
        Float value or None if invalid.
    """
    if not pct_str or str(pct_str).lower() == 'nan':
        return None
    try:
        return float(str(pct_str).replace('%', '').strip())
    except ValueError:
        return None


def parse_number(num_str: str) -> float | None:
    """Parse numeric string to float.
    
    Args:
        num_str: Number like "5.8" or "NaN"
        
    Returns:
        Float value or None if invalid.
    """
    if not num_str or str(num_str).lower() == 'nan':
        return None
    try:
        return float(str(num_str).strip())
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


def process_row(row: dict[str, str]) -> dict[str, Any] | None:
    """Process a single CSV row into cleaned data.
    
    Args:
        row: Raw CSV row as dictionary.
        
    Returns:
        Cleaned row data or None if invalid.
    """
    result = row.get('Result', '')
    if not is_valid_result(result):
        return None
    
    # Basic fields
    raw_date = row.get('Date', '').strip()
    player_name = sanitize_for_csv(row.get('Player', ''))
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
    
    return {
        'id': row_id,
        'matchId': match_id,
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


@router.get(
    "",
    summary="Get tour logs data",
    description="Fetch and return cleaned tour log data from Google Sheets.",
)
@limiter.limit("20/minute")
async def get_tour_logs(request: Request) -> dict[str, Any]:
    """Fetch tour logs from Google Sheets and return cleaned data.
    
    Returns:
        Dictionary with success status and data array.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(TOUR_LOGS_CSV_URL)
            response.raise_for_status()
            
        # Parse CSV - handle latin-1 encoding
        import csv
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
             logger.warning("CSV headers missing, using hardcoded fieldnames")

        reader = csv.DictReader(StringIO(content), **params)
        
        # Process all valid rows
        # No more merging of rows - returning everything as-is
        processed_data = []
        for row in reader:
            processed = process_row(row)
            if processed:
                processed_data.append(processed)
        
        logger.info(f"Fetched {len(processed_data)} tour log entries")
        
        return {
            "success": True,
            "count": len(processed_data),
            "data": processed_data,
        }
        
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch tour logs: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch tour logs data")
    except Exception as e:
        logger.error(f"Error processing tour logs: {e}")
        raise HTTPException(status_code=500, detail="Error processing tour logs data")
