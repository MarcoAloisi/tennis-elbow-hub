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

    Also handles '62% (41/66)' and simple '41/66'.

    Args:
        text: Ratio string from the stats table.

    Returns:
        Tuple of (numerator, denominator, percentage).
    """
    text = text.strip()
    if not text:
        return (0, 0, 0.0)

    # Strategy 1: Look for the Ratio "X / Y" explicitly
    # This covers "X / Y = Z%", "Z% (X / Y)", and just "X / Y"
    # We prioritize finding the ratio because that gives us the raw counts
    ratio_match = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if ratio_match:
        num = int(ratio_match.group(1))
        denom = int(ratio_match.group(2))
        
        # Try to find percentage in the same string to be precise, otherwise calculate it
        # Handle 100% specially to avoid issues
        if num == denom and num > 0:
            pct = 100.0
        else:
            pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            if pct_match:
                pct = float(pct_match.group(1))
            else:
                pct = (num / denom * 100) if denom > 0 else 0.0
            
        return (num, denom, pct)

    # Strategy 2: If no ratio found, look for just a percentage "62%"
    # We treat this as "62/0" which is not ideal but preserves the data
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if pct_match:
        pct = float(pct_match.group(1))
        return (int(pct), 0, pct)

    # Strategy 3: Try just a number "62"
    # match() is fine here as we want to ensure it's the main content if nothing else matched
    # But text might be "226 Km/h", so we look for \d+
    val_match = re.match(r"(\d+)", text)
    if val_match:
        return (int(val_match.group(1)), 0, 0.0)

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


def parse_duration(duration_str: str) -> str:
    """Normalize duration string and validate format.
    
    Expected format: H:MM'SS or MM'SS
    Returns normalized string or original if parsing fails.
    """
    try:
        # Try to parse with standard format
        if "'" in duration_str:
            # Replace ' with : for standard time parsing if needed, 
            # but for now we just want to ensure it is valid
            pass
        return duration_str
    except Exception:
        return duration_str


def extract_header_info(soup: BeautifulSoup) -> MatchInfo | None:
    """Extract match information from the HTML header.

    Expected formats:
    1. STRICT: "Player1 (ELO: ...) def. Player2 (ELO: ...) : Score - Tournament - Duration (Real) - Date [Online]"
    2. CPU/Other: "Player1 def. Player2 : Score - Tournament - Duration (Real) - Date"

    Args:
        soup: BeautifulSoup object of the HTML.

    Returns:
        MatchInfo model or None if parsing fails.
    """
    try:
        # Find paragraphs that contain match info
        for p in soup.find_all("p"):
            text = p.get_text().strip()

            # Trigger: Look for <p> tags that contain match separators
            # EN: "def.", FR: "bat.", ES: "vs", PL: "Przegrana"
            separators = [" def. ", " bat. ", " vs ", " Przegrana "]
            if not any(sep in text for sep in separators):
                continue

            logger.debug(f"Found header candidate: {text[:100]}")

            # Define Regex Patterns
            
            # Separator regex: handles EN/FR/ES/PL separators
            sep_pattern = r"(?: def\. | bat\. | vs | Przegrana )"
            
            # Strict Pattern (User Hint): (.*?) \(ELO: (.*?)\) [sep] (.*?) \(ELO: (.*?)\) : (.*?) - (.*?) - (.*?) - (.*)
            strict_pattern = re.compile(
                r"(.*?) \(ELO: (.*?)\)" + sep_pattern + r"(.*?) \(ELO: (.*?)\)\s*:\s*(.*?) - (.*?) - (.*?) - (.*)"
            )
            
            # Fallback Pattern
            fallback_pattern = re.compile(
                r"(.*?)" + sep_pattern + r"(.*?)\s*:\s*(.*?) - (.*?) - (.*?) - (.*)"
            )

            # Try Strict Match First
            match = strict_pattern.match(text)
            if match:
                groups = match.groups()
                # Groups: 
                # 1: P1 Name, 2: P1 ELO, 3: P2 Name, 4: P2 ELO
                # 5: Score, 6: Tournament, 7: Duration, 8: Date + [Online]
                
                player1_name = groups[0].strip()
                # player1_elo = groups[1].strip()
                player2_name = groups[2].strip()
                # player2_elo = groups[3].strip()
                score = groups[4].strip()
                tournament = groups[5].strip()
                duration_part = groups[6].strip()
                date_str = groups[7].strip()

                logger.info(f"Header Matched! Groups: {groups}")

                # Parse ELOs if available
                p1_elo_val = None
                p2_elo_val = None
                p1_diff_val = None
                p2_diff_val = None
                
                # Check for ELO in group 2 and 4 from strict match
                if groups[1] and groups[1].strip():
                    m = re.match(r"(\d+)(?:\s*([+-]\d+))?", groups[1].strip())
                    if m:
                        try:
                            p1_elo_val = int(m.group(1))
                            if m.group(2):
                                p1_diff_val = int(m.group(2))
                            logger.info(f"P1 ELO: {p1_elo_val}, Diff: {p1_diff_val}")
                        except ValueError:
                            pass
                
                if groups[3] and groups[3].strip():
                    m = re.match(r"(\d+)(?:\s*([+-]\d+))?", groups[3].strip())
                    if m:
                        try:
                            p2_elo_val = int(m.group(1))
                            if m.group(2):
                                p2_diff_val = int(m.group(2))
                            logger.info(f"P2 ELO: {p2_elo_val}, Diff: {p2_diff_val}")
                        except ValueError:
                            pass
                        
            else:
                # Try Fallback
                match = fallback_pattern.match(text)
                p1_elo_val = None
                p2_elo_val = None
                p1_diff_val = None
                p2_diff_val = None

                if match:
                    groups = match.groups()
                    # Groups: 1: P1, 2: P2, 3: Score, 4: Tourn, 5: Duration, 6: Date+Online
                    raw_p1 = groups[0].strip()
                    raw_p2 = groups[1].strip()
                    
                    # Extract ELO from names if present: "Name (ELO: 1234 ...)"
                    p1_elo_match = re.search(r"\(ELO:\s*(\d+)", raw_p1)
                    if p1_elo_match:
                         try:
                             p1_elo_val = int(p1_elo_match.group(1))
                         except ValueError:
                             pass
                    
                    p2_elo_match = re.search(r"\(ELO:\s*(\d+)", raw_p2)
                    if p2_elo_match:
                         try:
                             p2_elo_val = int(p2_elo_match.group(1))
                         except ValueError:
                             pass

                    # Clean names: remove (ELO: ...) block entirely
                    player1_name = re.sub(r"\s*\(ELO:.*?\)", "", raw_p1).strip()
                    player2_name = re.sub(r"\s*\(ELO:.*?\)", "", raw_p2).strip()
                    
                    score = groups[2].strip()
                    tournament = groups[3].strip()
                    duration_part = groups[4].strip()
                    date_str = groups[5].strip()
                else:
                    # Legacy Split Logic (Safety Net)
                    # Handle all language separators
                    if " bat. " in text:
                        parts = text.split(" bat. ", 1)
                    elif " vs " in text:
                        parts = text.split(" vs ", 1)
                    elif " Przegrana " in text:
                        parts = text.split(" Przegrana ", 1)
                    else:
                        parts = text.split(" def. ", 1)
                        
                    raw_p1 = parts[0].strip()
                    
                    # Handle checkbox garbage matching
                    raw_p1 = re.sub(r"^.*?([A-Za-z])", r"\1", raw_p1) 
                    
                    p1_elo_match = re.search(r"\(ELO:\s*(\d+)", raw_p1)
                    if p1_elo_match:
                         try:
                             p1_elo_val = int(p1_elo_match.group(1))
                         except ValueError:
                             pass
                             
                    player1_name = re.sub(r"\s*\(ELO:.*?\)", "", raw_p1).strip()

                    rest = parts[1].strip()
                    
                    # Determine split point for score (colon)
                    split_match = re.search(r"\s*:\s*", rest)
                    
                    if split_match:
                        start, end = split_match.span()
                        raw_p2 = rest[:start].strip()
                        details = rest[end:].strip()
                        
                        p2_elo_match = re.search(r"\(ELO:\s*(\d+)", raw_p2)
                        if p2_elo_match:
                             try:
                                 p2_elo_val = int(p2_elo_match.group(1))
                             except ValueError:
                                 pass
                                 
                        player2_name = re.sub(r"\s*\(ELO:.*?\)", "", raw_p2).strip()
                        
                        detail_parts = [x.strip() for x in details.split(" - ")]
                        score = detail_parts[0] if len(detail_parts) > 0 else ""
                        tournament = detail_parts[1] if len(detail_parts) > 1 else ""
                        duration_part = detail_parts[2] if len(detail_parts) > 2 else ""
                        date_str = detail_parts[3] if len(detail_parts) > 3 else ""
                        # Strip [Online] from date if present in split
                        date_str = date_str.replace("[Online]", "").strip()
                    else:
                        continue

            # Clean Player Checkboxes if regex captured them
            player1_name = player1_name.strip()
            player2_name = player2_name.strip()

            # Parse Duration
            duration = ""
            real_duration = ""
            dur_match = re.match(r"([\d:\']+)\s*\(([\d:\']+)\)", duration_part)
            if dur_match:
                duration = dur_match.group(1)
                real_duration = dur_match.group(2)
            else:
                duration = duration_part

            # Parse Date
            match_date = None
            if date_str:
                date_clean = date_str.replace("[Online]", "").strip()
                try:
                    match_date = datetime.strptime(date_clean, "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        match_date = datetime.strptime(date_clean, "%Y-%m-%d")
                    except ValueError:
                        pass
            
            # Check for Retirement ("ret." used in EN/ES/FR, "ab." for abandon)
            is_retirement = "ret." in score.lower() or "ab." in score.lower()

            return MatchInfo(
                player1_name=player1_name,
                player2_name=player2_name,
                score=score,
                tournament=tournament,
                duration=duration,
                real_duration=real_duration,
                date=match_date,
                is_retirement=is_retirement,
                player1_elo=p1_elo_val,
                player2_elo=p2_elo_val,
                player1_elo_diff=p1_diff_val,
                player2_elo_diff=p2_diff_val,
            )

        return None

    except Exception as e:
        logger.error(f"Failed to extract header info: {e}")
        return None


StatsRow = dict[str, str | None]

def extract_stats_from_table(soup: BeautifulSoup) -> list[StatsRow]:
    """Extract statistics from the HTML table by position.

    The TE4 table format has 6 or 7 columns per row.
    We extract rows into a structured list where each row has:
    - left_p1, left_label, left_p2
    - right_p1, right_label, right_p2 (optional)

    Args:
        soup: BeautifulSoup object of the HTML.

    Returns:
        List of dictionaries containing row data.
    """
    rows_data: list[StatsRow] = []

    # Find the main stats table
    # The file might have multiple tables if checkboxes are present, 
    # but usually the stats are in the table following the header.
    # We iterate all tables and look for the one with stats structure.
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        current_table_rows: list[StatsRow] = []
        is_valid_stats_table = False

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                # Basic row structure
                row_item: StatsRow = {
                    "left_p1": cells[0].get_text().strip(),
                    "left_p2": cells[2].get_text().strip(),
                    "left_label": cells[1].get_text().strip(),
                    "right_p1": None,
                    "right_p2": None,
                    "right_label": None,
                }
                
                # Check for second group (columns 4, 5, 6)
                # cell 3 is spacer
                if len(cells) >= 7:
                     row_item["right_p1"] = cells[4].get_text().strip()
                     row_item["right_label"] = cells[5].get_text().strip()
                     row_item["right_p2"] = cells[6].get_text().strip()
                
                current_table_rows.append(row_item)
                
                # Heuristic to identify this as the stats table:
                # Look for known percentage signs or '/' in values, or specific structure length
                p1_val = row_item["left_p1"]
                if "/" in str(p1_val) or "%" in str(p1_val):
                    is_valid_stats_table = True

        if is_valid_stats_table and len(current_table_rows) >= 10:
            # We found the stats table (it usually has ~12 rows)
            rows_data = current_table_rows
            break
            
    return rows_data


def get_val(rows: list[StatsRow], r: int, side: str, p_idx: int) -> str:
    """Helper to safely get a value from rows list.
    
    Args:
        rows: The list of row data
        r: Row index
        side: "left" or "right"
        p_idx: 0 (player 1) or 1 (player 2)
    """
    if r >= len(rows):
        return "0"
    
    key = f"{side}_p{p_idx + 1}"
    val = rows[r].get(key)
    return str(val) if val is not None else "0"


def extract_rally_length(rows: list[StatsRow]) -> float:
    """Extract average rally length from Row 3 (Right side).
    
    The value is usually embedded in the label: "AVERAGE RALLY LENGTH: 4.6"
    or in other languages: "Longueur moyenne des échanges: 3.4"
    """
    if len(rows) <= 3:
        return 0.0
        
    label = rows[3].get("right_label", "")
    if label:
        match = re.search(r"(\d+(?:\.\d+)?)", label)
        if match:
            return float(match.group(1))
    return 0.0


def build_player_stats(
    rows: list[StatsRow],
    player_index: int,
    player_name: str,
    elo: int | None = None,
    elo_diff: int | None = None,
) -> PlayerMatchStats:
    """Build player statistics from extracted positional data.

    Args:
        rows: List of row data dictionaries.
        player_index: 0 for player 1, 1 for player 2.
        player_name: Player name.
        elo: Player ELO rating.
        elo_diff: Player ELO change.

    Returns:
        PlayerMatchStats model.
    """
    # MAPPING STRATEGY (Based on TE4 English & French logs)
    # Row 0: Left=1st Serve %, Right=Short Rallies Won
    # Row 1: Left=Aces, Right=Medium Rallies Won
    # Row 2: Left=Double Faults, Right=Long Rallies Won
    # Row 3: Left=Fastest Serve, Right=Avg Rally Length (Label)
    # Row 4: Left=Avg 1st Serve Speed, Right=Set Points Saved
    # Row 5: Left=Avg 2nd Serve Speed, Right=Match Points Saved
    # Row 6: Left=Winners, Right=1st Serve Won %
    # Row 7: Left=Forced Errors, Right=2nd Serve Won %
    # Row 8: Left=Unforced Errors, Right=Return Points Won
    # Row 9: Left=Net Points Won, Right=Return Winners
    # Row 10: Left=Break Points Won, Right=Breaks/Games
    # Row 11: Left=Total Points Won

    def val(r: int, side: str) -> str:
        return get_val(rows, r, side, player_index)

    # Parse serve stats
    # Row 0 Left: 1st Serve %
    first_serve = parse_ratio(val(0, "left"))
    
    # Row 1 Left: Aces
    aces = parse_ratio(val(1, "left"))[0]
    
    # Row 2 Left: Double Faults
    dfs = parse_ratio(val(2, "left"))[0]
    
    # Row 3 Left: Fastest Serve
    fastest = parse_speed(val(3, "left"))
    
    # Row 4 Left: Avg 1st Serve
    avg_1st = parse_speed(val(4, "left"))
    
    # Row 5 Left: Avg 2nd Serve
    avg_2nd = parse_speed(val(5, "left"))

    serve = ServeStats(
        first_serve_in=first_serve[0],
        first_serve_total=first_serve[1],
        first_serve_pct=first_serve[2],
        aces=aces,
        double_faults=dfs,
        fastest_serve_kmh=fastest,
        avg_first_serve_kmh=avg_1st,
        avg_second_serve_kmh=avg_2nd,
    )

    # Parse rally stats
    # Row 0 Right: Short Rallies
    short_rallies = parse_ratio(val(0, "right"))
    # Row 1 Right: Medium Rallies
    normal_rallies = parse_ratio(val(1, "right"))
    # Row 2 Right: Long Rallies
    long_rallies = parse_ratio(val(2, "right"))
    # Row 3 Right: Avg Rally Length (Extracted from label, shared for both players usually, but logic is generic)
    avg_rally = extract_rally_length(rows)

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
    # Row 6 Left: Winners
    winners = parse_ratio(val(6, "left"))[0]
    # Row 7 Left: Forced Errors
    forced = parse_ratio(val(7, "left"))[0]
    # Row 8 Left: Unforced Errors
    unforced = parse_ratio(val(8, "left"))[0]
    
    # Row 9 Left: Net Points Won
    net_pts = parse_ratio(val(9, "left"))
    
    # Row 6 Right: 1st Serve Won %
    first_won = parse_ratio(val(6, "right"))
    # Row 7 Right: 2nd Serve Won %
    second_won = parse_ratio(val(7, "right"))
    
    # Row 8 Right: Return Points Won
    ret_pts = parse_ratio(val(8, "right"))
    
    # Row 9 Right: Return Winners
    ret_winners_val = val(9, "right")
    # Sometimes Row 9 Right is empty or diff? English says "RETURN WINNERS" at Row 9 Right
    ret_winners = parse_ratio(ret_winners_val)[0]
    
    # Row 11 Left: Total Points Won
    total_won = parse_ratio(val(11, "left"))[0]

    points = PointStats(
        winners=winners,
        forced_errors=forced,
        unforced_errors=unforced,
        net_points_won=net_pts[0],
        net_points_total=net_pts[1],
        points_on_first_serve_won=first_won[0],
        points_on_first_serve_total=first_won[1],
        points_on_second_serve_won=second_won[0],
        points_on_second_serve_total=second_won[1],
        return_points_won=ret_pts[0],
        return_points_total=ret_pts[1],
        return_winners=ret_winners,
        total_points_won=total_won,
    )

    # Parse break point stats
    # Row 10 Left: Break Points Won
    bp_won = parse_ratio(val(10, "left"))
    # Row 10 Right: Breaks / Games
    # Careful: Row 10 Right is Breaks/Games, but break points saved is not explicitly there?
    # TE4 stats: "BREAK POINTS WON" is for the attacker. 
    # To get "Break Points Saved" for P1, we would look at P2's "BREAK POINTS WON" failure count?
    # But current logic was: set_points_saved = ???
    # Old logic: set_points_saved = parse_ratio(get_stat(["SET POINTS SAVED"]))[0]
    # Row 4 Right: Set Points Saved
    set_saved = parse_ratio(val(4, "right"))[0]
    # Row 5 Right: Match Points Saved
    match_saved = parse_ratio(val(5, "right"))[0]
    
    # Row 10 Right: Breaks / Games
    break_games = parse_ratio(val(10, "right"))

    break_points = BreakPointStats(
        break_points_won=bp_won[0],
        break_points_total=bp_won[1],
        break_games_won=break_games[0],
        break_games_total=break_games[1],
        set_points_saved=set_saved,
        match_points_saved=match_saved,
    )

    # General Stats
    # Import locally to avoid circulars if any, but models are separate
    from app.models.match_stats import GeneralStats
    general = GeneralStats(
        elo=elo,
        elo_diff=elo_diff
    )

    return PlayerMatchStats(
        name=player_name,
        general=general,
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

        # Extract raw_match_id from table element
        table = soup.find("table")
        raw_match_id = table.get("id") if table else None

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
                raw_match_id=raw_match_id,
            )
        else:
            # Add raw_match_id to the extracted info
            info.raw_match_id = raw_match_id

        # Extract stats from table
        stats = extract_stats_from_table(soup)
        logger.info(f"Extracted {len(stats)} stat rows")

        # Build player stats
        player1 = build_player_stats(
            stats, 
            0, 
            info.player1_name,
            elo=info.player1_elo,
            elo_diff=info.player1_elo_diff
        )
        player2 = build_player_stats(
            stats, 
            1, 
            info.player2_name,
            elo=info.player2_elo,
            elo_diff=info.player2_elo_diff
        )

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
        # EN: "def.", FR: "bat.", ES: "vs", PL: "Przegrana"
        chunk_separators = [" def. ", " bat. ", " vs ", " Przegrana "]
        if not any(sep in chunk for sep in chunk_separators):
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
