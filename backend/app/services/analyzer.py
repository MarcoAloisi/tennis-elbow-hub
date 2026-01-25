"""Analyzer service for parsing match log HTML files.

This module handles parsing of Tennis Elbow 4 match log HTML files
and extracts detailed statistics for both players.
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.models.match_stats import (
    BreakPointStats,
    MatchAnalysisResponse,
    MatchInfo,
    MatchStats,
    PlayerMatchStats,
    PointStats,
    RallyStats,
    ServeStats,
)

logger = get_logger("analyzer")


def parse_ratio(text: str) -> tuple[int, int, float]:
    """Parse a ratio string like '41 / 66 = 62%' into components.

    Args:
        text: Ratio string from the stats table.

    Returns:
        Tuple of (numerator, denominator, percentage).
    """
    text = text.strip()
    if not text:
        return (0, 0, 0.0)

    # Try full format: "X / Y = Z%"
    match = re.match(r"(\d+)\s*/\s*(\d+)\s*=\s*(\d+(?:\.\d+)?)\s*%?", text)
    if match:
        num = int(match.group(1))
        denom = int(match.group(2))
        pct = float(match.group(3))
        return (num, denom, pct)

    # Try simple ratio: "X / Y"
    match = re.match(r"(\d+)\s*/\s*(\d+)", text)
    if match:
        num = int(match.group(1))
        denom = int(match.group(2))
        pct = (num / denom * 100) if denom > 0 else 0.0
        return (num, denom, pct)

    # Try just a number
    match = re.match(r"(\d+)", text)
    if match:
        return (int(match.group(1)), 0, 0.0)

    return (0, 0, 0.0)


def parse_speed(text: str) -> float:
    """Parse a speed value like '222 Km/h'.

    Args:
        text: Speed string.

    Returns:
        Speed as float, or 0 if parsing fails.
    """
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:Km/h|km/h|KM/H)?", text.strip())
    if match:
        return float(match.group(1))
    return 0.0


def extract_header_info(soup: BeautifulSoup) -> MatchInfo | None:
    """Extract match information from the HTML header.

    Expected format in a <p> tag:
    "Player1 (ELO: X +/-Y) def. Player2 (ELO: X +/-Y) : Score - Tournament - Duration (RealDuration) - Date [Online]"

    Args:
        soup: BeautifulSoup object of the HTML.

    Returns:
        MatchInfo model or None if parsing fails.
    """
    try:
        # Find paragraphs that contain match info
        for p in soup.find_all("p"):
            text = p.get_text().strip()

            # Look for the "def." pattern which indicates match result
            if " def. " not in text and " vs " not in text:
                continue

            logger.debug(f"Found header: {text[:100]}")

            # Parse format: "Player1 (ELO: X) def. Player2 (ELO: X) : Score - Tournament..."
            # Or checkbox variant with player info

            # Extract players - before and after "def." or "vs"
            if " def. " in text:
                parts = text.split(" def. ", 1)
            else:
                parts = text.split(" vs ", 1)

            if len(parts) < 2:
                continue

            player1_part = parts[0].strip()
            rest = parts[1].strip()

            # Clean player1 name (may have checkbox prefix)
            player1_name = re.sub(r"^.*?([A-Za-z])", r"\1", player1_part)
            # Remove ELO info
            player1_name = re.sub(r"\s*\(ELO:.*?\)", "", player1_name).strip()

            # Split rest by " : " to get player2 and match details
            if " : " in rest:
                player2_and_details = rest.split(" : ", 1)
                player2_part = player2_and_details[0]
                details = player2_and_details[1] if len(player2_and_details) > 1 else ""
            else:
                player2_part = rest
                details = ""

            # Clean player2 name
            player2_name = re.sub(r"\s*\(ELO:.*?\)", "", player2_part).strip()

            # Parse details: "Score - Tournament - Duration (RealDuration) - Date [Online]"
            detail_parts = [x.strip() for x in details.split(" - ")]
            score = detail_parts[0] if len(detail_parts) > 0 else ""
            tournament = detail_parts[1] if len(detail_parts) > 1 else ""
            duration = ""
            real_duration = ""
            match_date = None

            if len(detail_parts) > 2:
                duration_part = detail_parts[2]
                dur_match = re.match(r"([\d:\']+)\s*\(([\d:\']+)\)", duration_part)
                if dur_match:
                    duration = dur_match.group(1)
                    real_duration = dur_match.group(2)
                else:
                    duration = duration_part

            if len(detail_parts) > 3:
                date_str = detail_parts[3].replace("[Online]", "").strip()
                try:
                    match_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        match_date = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        pass

            return MatchInfo(
                player1_name=player1_name,
                player2_name=player2_name,
                score=score,
                tournament=tournament,
                duration=duration,
                real_duration=real_duration,
                date=match_date,
            )

        return None

    except Exception as e:
        logger.error(f"Failed to extract header info: {e}")
        return None


def extract_stats_from_table(soup: BeautifulSoup) -> dict[str, tuple[str, str]]:
    """Extract statistics from the HTML table.

    The TE4 table format has 6 or 7 columns per row:
    - Col 0: Player 1 value (left stat)
    - Col 1: Label (left stat)
    - Col 2: Player 2 value (left stat)
    - Col 3: Spacer
    - Col 4: Player 1 value (right stat)
    - Col 5: Label (right stat)
    - Col 6: Player 2 value (right stat)

    Args:
        soup: BeautifulSoup object of the HTML.

    Returns:
        Dictionary mapping stat labels to (player1_value, player2_value).
    """
    stats: dict[str, tuple[str, str]] = {}

    # Find all tables
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                # First stat group (columns 0, 1, 2)
                p1_val = cells[0].get_text().strip()
                label = cells[1].get_text().strip()
                p2_val = cells[2].get_text().strip()

                if label and label != "&nbsp;":
                    # Normalize label
                    label_normalized = label.upper().strip()
                    stats[label_normalized] = (p1_val, p2_val)

                # Second stat group (columns 4, 5, 6) if present
                if len(cells) >= 7 and cells[3].get_text().strip() in ("", "\xa0"):
                    p1_val2 = cells[4].get_text().strip()
                    label2 = cells[5].get_text().strip()
                    p2_val2 = cells[6].get_text().strip() if len(cells) > 6 else ""

                    if label2 and label2 != "&nbsp;":
                        label2_normalized = label2.upper().strip()
                        stats[label2_normalized] = (p1_val2, p2_val2)

    return stats


def get_stat_value(
    stats: dict[str, tuple[str, str]],
    labels: list[str],
    player_index: int,
) -> str:
    """Get stat value with fallback to multiple label variants.

    Args:
        stats: Dictionary of stats.
        labels: List of possible label names (checked in order).
        player_index: 0 for player 1, 1 for player 2.

    Returns:
        The stat value or "0" if not found.
    """
    for label in labels:
        label_upper = label.upper()
        if label_upper in stats:
            return stats[label_upper][player_index]
    return "0"


def extract_avg_rally_length(stats: dict[str, tuple[str, str]]) -> float:
    """Extract average rally length from stats.

    The format is: "AVERAGE RALLY LENGTH: 4.6"

    Args:
        stats: Dictionary of stats.

    Returns:
        Average rally length as float.
    """
    for label in stats.keys():
        if "AVERAGE RALLY LENGTH" in label:
            match = re.search(r"(\d+(?:\.\d+)?)", label)
            if match:
                return float(match.group(1))
    return 0.0


def build_player_stats(
    stats: dict[str, tuple[str, str]],
    player_index: int,
    player_name: str,
) -> PlayerMatchStats:
    """Build player statistics from extracted data.

    Args:
        stats: Dictionary of stat labels to values.
        player_index: 0 for player 1, 1 for player 2.
        player_name: Player name.

    Returns:
        PlayerMatchStats model.
    """

    def get_stat(labels: list[str]) -> str:
        return get_stat_value(stats, labels, player_index)

    # Parse serve stats
    first_serve = parse_ratio(get_stat(["1ST SERVE %", "FIRST SERVE %"]))
    serve = ServeStats(
        first_serve_in=first_serve[0],
        first_serve_total=first_serve[1],
        first_serve_pct=first_serve[2],
        aces=parse_ratio(get_stat(["ACES"]))[0],
        double_faults=parse_ratio(get_stat(["DOUBLE FAULTS"]))[0],
        fastest_serve_kmh=parse_speed(get_stat(["FASTEST SERVE"])),
        avg_first_serve_kmh=parse_speed(get_stat(["AVG 1ST SERVE SPEED"])),
        avg_second_serve_kmh=parse_speed(get_stat(["AVG 2ND SERVE SPEED"])),
    )

    # Parse rally stats
    short_rallies = parse_ratio(get_stat(["SHORT RALLIES WON (< 5)"]))
    normal_rallies = parse_ratio(get_stat(["MEDIUM RALLIES WON (5-8)"]))
    long_rallies = parse_ratio(get_stat(["LONG RALLIES WON (> 8)"]))
    avg_rally = extract_avg_rally_length(stats)

    rally = RallyStats(
        short_rallies_won=short_rallies[0],
        short_rallies_total=short_rallies[1],
        normal_rallies_won=normal_rallies[0],
        normal_rallies_total=normal_rallies[1],
        long_rallies_won=long_rallies[0],
        long_rallies_total=long_rallies[1],
        avg_rally_length=avg_rally,
    )

    # Parse point stats
    net_points = parse_ratio(get_stat(["NET POINTS WON"]))
    first_serve_pts = parse_ratio(get_stat(["1ST SERVE WON %"]))
    second_serve_pts = parse_ratio(get_stat(["2ND SERVE WON %"]))
    return_pts = parse_ratio(get_stat(["RETURN POINTS WON"]))

    points = PointStats(
        winners=parse_ratio(get_stat(["WINNERS"]))[0],
        forced_errors=parse_ratio(get_stat(["FORCED ERRORS"]))[0],
        unforced_errors=parse_ratio(get_stat(["UNFORCED ERRORS"]))[0],
        net_points_won=net_points[0],
        net_points_total=net_points[1],
        points_on_first_serve_won=first_serve_pts[0],
        points_on_first_serve_total=first_serve_pts[1],
        points_on_second_serve_won=second_serve_pts[0],
        points_on_second_serve_total=second_serve_pts[1],
        return_points_won=return_pts[0],
        return_points_total=return_pts[1],
        total_points_won=parse_ratio(get_stat(["TOTAL POINTS WON"]))[0],
    )

    # Parse break point stats
    break_pts = parse_ratio(get_stat(["BREAK POINTS WON"]))
    break_games = parse_ratio(get_stat(["BREAKS / GAMES"]))

    break_points = BreakPointStats(
        break_points_won=break_pts[0],
        break_points_total=break_pts[1],
        break_games_won=break_games[0],
        set_points_saved=parse_ratio(get_stat(["SET POINTS SAVED"]))[0],
        match_points_saved=parse_ratio(get_stat(["MATCH POINTS SAVED"]))[0],
    )

    return PlayerMatchStats(
        name=player_name,
        serve=serve,
        rally=rally,
        points=points,
        break_points=break_points,
    )


def analyze_match_log(html_content: str) -> MatchStats | None:
    """Analyze a match log HTML file and extract statistics.

    Args:
        html_content: Raw HTML content of the match log.

    Returns:
        MatchStats model with complete statistics, or None if parsing fails.
    """
    try:
        soup = BeautifulSoup(html_content, "lxml")

        # Extract header info
        info = extract_header_info(soup)
        if not info:
            logger.warning("Failed to extract match info from header, using defaults")
            info = MatchInfo(
                player1_name="Player 1",
                player2_name="Player 2",
                score="",
                tournament="",
                duration="",
                real_duration="",
            )

        # Extract stats from table
        stats = extract_stats_from_table(soup)
        logger.info(f"Extracted {len(stats)} stat rows")

        # Build player stats
        player1 = build_player_stats(stats, 0, info.player1_name)
        player2 = build_player_stats(stats, 1, info.player2_name)

        return MatchStats(
            info=info,
            player1=player1,
            player2=player2,
        )

    except Exception as e:
        logger.error(f"Failed to analyze match log: {e}")
        return None


def parse_match_log_file(html_content: str) -> list[MatchStats]:
    """Parse a full match log file containing multiple matches.

    Args:
        html_content: Raw HTML content of the match log.

    Returns:
        List of MatchStats models.
    """
    matches: list[MatchStats] = []
    
    # Split by horizontal rules <hr> which separate matches
    # TE4 logs separate matches with <hr> or <hr/> or <hr >
    # We'll split by regex to be safe
    chunks = re.split(r"<hr\s*\/?>", html_content, flags=re.IGNORECASE)
    
    logger.info(f"Found {len(chunks)} potential match chunks")
    
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue

        # Check for valid match indicators before parsing
        if " def. " not in chunk and " vs " not in chunk:
            logger.debug(f"Skipping chunk {i} - no match indicators found")
            continue
            
        try:
            stats = analyze_match_log(chunk)
            # Only add if we actually extracted stats or have valid header info
            if stats and (stats.player1.points.total_points_won > 0 or (stats.info and stats.info.score)):
                 matches.append(stats)
            elif stats and stats.info.score:
                 # Case where we have info but maybe no stats table (rare)
                 matches.append(stats)
            else:
                 logger.debug(f"Skipping chunk {i} - parsed stats appeared empty/invalid")
        except Exception as e:
            logger.warning(f"Failed to parse match chunk {i}: {e}")
            continue
            
    return matches


async def process_uploaded_file(
    content: bytes,
    filename: str,
) -> MatchAnalysisResponse:
    """Process an uploaded match log file.

    Args:
        content: File contents as bytes.
        filename: Original filename.

    Returns:
        MatchAnalysisResponse with results or error.
    """
    try:
        # Decode content - try multiple encodings
        html_content = None
        for encoding in ["utf-8", "iso-8859-1", "latin-1", "cp1252"]:
            try:
                html_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if html_content is None:
            return MatchAnalysisResponse(
                success=False,
                error="Could not decode file with any supported encoding",
                filename=filename,
            )

        # Analyze the match log
        matches = parse_match_log_file(html_content)

        if matches:
            return MatchAnalysisResponse(
                success=True,
                matches=matches,
                stats=matches[0] if matches else None,  # For backward compatibility
                filename=filename,
            )
        else:
            return MatchAnalysisResponse(
                success=False,
                error="Failed to parse any matches from file",
                filename=filename,
            )

    except Exception as e:
        logger.error(f"Error processing file {filename}: {e}")
        return MatchAnalysisResponse(
            success=False,
            error=str(e),
            filename=filename,
        )
