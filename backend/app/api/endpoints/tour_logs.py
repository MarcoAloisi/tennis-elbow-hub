"""WTSL Tour Logs API endpoints.

Fetches and processes tour log data from Google Sheets CSV.
"""

import re
from io import StringIO
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger

logger = get_logger("api.tour_logs")
router = APIRouter(prefix="/tour-logs", tags=["Tour Logs"])

# Google Sheets published CSV URL
TOUR_LOGS_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vSSmOIpik7GxM7cLpuO6H1lCIDGZHs229frl1t_MKBtiwnT394nTWRMXGpeSEc8wLUwC8CEcq6OIPX6"
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
    return date_str.split()[0] if ' ' in date_str else date_str


def parse_elo(elo_str: str) -> tuple[int | None, bool | None]:
    """Extract numeric ELO and win/loss indicator from string.
    
    Args:
        elo_str: ELO string like "1870 +27" or "1870 -15" or "NaN"
        
    Returns:
        Tuple of (ELO value, is_win boolean). 
        is_win is True if +, False if -, None if unknown.
    """
    if not elo_str or elo_str.lower() == 'nan':
        return None, None
    try:
        parts = elo_str.split()
        elo_value = int(parts[0])
        is_win = None
        if len(parts) > 1:
            delta = parts[1]
            if delta.startswith('+'):
                is_win = True
            elif delta.startswith('-'):
                is_win = False
        return elo_value, is_win
    except (ValueError, IndexError):
        return None, None


def parse_percentage(pct_str: str) -> float | None:
    """Parse percentage string to float.
    
    Args:
        pct_str: Percentage like "86%" or "NaN"
        
    Returns:
        Float value or None if invalid.
    """
    if not pct_str or pct_str.lower() == 'nan':
        return None
    try:
        return float(pct_str.replace('%', '').strip())
    except ValueError:
        return None


def parse_number(num_str: str) -> float | None:
    """Parse numeric string to float.
    
    Args:
        num_str: Number like "5.8" or "NaN"
        
    Returns:
        Float value or None if invalid.
    """
    if not num_str or num_str.lower() == 'nan':
        return None
    try:
        return float(num_str.strip())
    except ValueError:
        return None


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
    
    # Parse ELO with win indicator
    player_elo, player_won = parse_elo(row.get('ELO', ''))
    opponent_elo, _ = parse_elo(row.get('Opponent ELO', ''))
    
    # Keep full date with time for deduplication
    raw_date = row.get('Date', '').strip()
    
    return {
        'imageName': row.get('Image Name', '').strip(),  # For unique match ID
        'player': row.get('Player', '').strip(),
        'elo': player_elo,
        'playerWon': player_won,  # True if +, False if -, None if unknown
        'crc': row.get('Crc', '').strip(),
        'result': result.strip(),
        'opponent': row.get('Opponent', '').strip(),
        'opponentElo': opponent_elo,
        'opponentCrc': row.get('Opponent Crc', '').strip(),
        'tournament': row.get('Tournament', '').strip(),
        'dateTime': raw_date,  # Full date+time for deduplication
        'date': clean_date(raw_date),  # Cleaned date for display
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
async def get_tour_logs() -> dict[str, Any]:
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
        reader = csv.DictReader(StringIO(content))
        
        # Process all rows first
        all_rows = []
        for row in reader:
            processed = process_row(row)
            if processed:
                all_rows.append(processed)
        
        # Create match key for pairing rows
        def create_match_key(row):
            players = sorted([row['player'].lower(), row['opponent'].lower()])
            return f"{row['dateTime']}|{row['imageName']}|{players[0]}|{players[1]}"
        
        # Group rows by match key
        matches = {}
        for row in all_rows:
            key = create_match_key(row)
            if key not in matches:
                matches[key] = []
            matches[key].append(row)
        
        # Merge winner/loser stats - keep winner row and add opponent stats
        merged_data = []
        for key, rows in matches.items():
            winner = None
            loser = None
            
            for row in rows:
                if row.get('playerWon') is True:
                    winner = row
                elif row.get('playerWon') is False:
                    loser = row
            
            if winner:
                # Add opponent stats from loser's row
                if loser:
                    winner['oppFirstServePct'] = loser.get('firstServePct')
                    winner['oppAces'] = loser.get('aces')
                    winner['oppDoubleFaults'] = loser.get('doubleFaults')
                    winner['oppFastestServe'] = loser.get('fastestServe')
                    winner['oppAvgFirstServeSpeed'] = loser.get('avgFirstServeSpeed')
                    winner['oppAvgSecondServeSpeed'] = loser.get('avgSecondServeSpeed')
                    winner['oppWinners'] = loser.get('winners')
                    winner['oppForcedErrors'] = loser.get('forcedErrors')
                    winner['oppUnforcedErrors'] = loser.get('unforcedErrors')
                    winner['oppTotalPointsWon'] = loser.get('totalPointsWon')
                    winner['oppNetPointsWonPct'] = loser.get('netPointsWonPct')
                    winner['oppReturnPointsWonPct'] = loser.get('returnPointsWonPct')
                    winner['oppReturnWinners'] = loser.get('returnWinners')
                    winner['oppBreakPointsWonPct'] = loser.get('breakPointsWonPct')
                    winner['oppBreaksPerGamePct'] = loser.get('breaksPerGamePct')
                    winner['oppFirstServeWonPct'] = loser.get('firstServeWonPct')
                    winner['oppSecondServeWonPct'] = loser.get('secondServeWonPct')
                
                merged_data.append(winner)
        
        logger.info(f"Fetched {len(merged_data)} unique matches with merged stats")
        
        return {
            "success": True,
            "count": len(merged_data),
            "data": merged_data,
        }
        
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch tour logs: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch tour logs data")
    except Exception as e:
        logger.error(f"Error processing tour logs: {e}")
        raise HTTPException(status_code=500, detail="Error processing tour logs data")
