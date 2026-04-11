"""Stats tracking service.

Tracks finished matches (5+ games) and persists daily statistics.
Stateless implementation relying on Database for concurrency safety.
"""

import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.logging import get_logger
from app.models.daily_stats import DailyStats
from app.models.finished_match import FinishedMatch
from app.models.game_server import GameServer
from app.models.player_alias import PlayerAlias

logger = get_logger("stats_service")


class StatsService:
    """Service for tracking and persisting match statistics.
    
    This service is stateless and relies on the database unique constraints
    to handle concurrency safely across multiple workers.
    """

    # Minimum games required to count a match as "played"
    MIN_GAMES_THRESHOLD = 5

    def __init__(self) -> None:
        """Initialize the stats service."""
        self.settings = get_settings()
        self.timezone = ZoneInfo(self.settings.stats_timezone)
        
        # We only keep previous_matches in memory to detect transitions
        # This is safe per-worker because it's only for change detection,
        # the actual "counting" is enforced by the DB.
        self._previous_matches: dict[str, GameServer] = {}

    def _get_today(self) -> date:
        """Get current date in configured timezone."""
        return datetime.now(self.timezone).date()

    def _detect_mod(self, server: GameServer) -> str:
        """Detect mod type from server tag_line."""
        tag = (server.tag_line or "").lower()
        if "wtsl" in tag:
            return "wtsl"
        elif "xkt" in tag:
            return "xkt"
        return "vanilla"

    def _detect_format(self, server: GameServer) -> str:
        """Detect match format from game_info.nb_set."""
        nb_set = server.game_info.nb_set
        if nb_set in (0, 1):
            return "bo1"
        elif nb_set == 2:
            return "bo3"
        elif nb_set == 3:
            return "bo5"
        return "bo1"  # Default

    async def track_matches(self, current_servers: list[GameServer]) -> int:
        """Track finished matches from the current server list.

        Args:
            current_servers: Current list of live servers.

        Returns:
            Number of newly finished matches detected.
        """
        today = self._get_today()
        
        # Build current matches dict
        current_matches = {s.match_id: s for s in current_servers}
        
        # Identify potentially finished matches (in previous but not in current)
        previous_ids = set(self._previous_matches.keys())
        current_ids = set(current_matches.keys())
        missing_ids = previous_ids - current_ids
        new_ids = current_ids - previous_ids
        
        # Helper for rename detection
        def _get_identity_key(s: GameServer) -> tuple:
            return (
                s.creation_time_ms,
                s.port,
                s.surface_name,
                s.game_info.nb_set,
                s.game_info.player_config,
            )
            
        new_matches_by_identity = {
            _get_identity_key(current_matches[mid]): mid
            for mid in new_ids
        }

        finished_count = 0
        
        for match_id in missing_ids:
            server = self._previous_matches[match_id]
            
            # 1. RENAME DETECTION
            identity_key = _get_identity_key(server)
            migrated_id = new_matches_by_identity.get(identity_key)
            
            if migrated_id:
                migrated_server = current_matches[migrated_id]
                p1_names = {n.lower().strip() for n in server.player_names if n != "Unknown"}
                p2_names = {n.lower().strip() for n in migrated_server.player_names if n != "Unknown"}
                is_p1_waiting = not p1_names or "waiting" in p1_names
                has_overlap = is_p1_waiting or not p2_names or bool(p1_names & p2_names)
                
                if has_overlap:
                    if migrated_server.nb_game >= server.nb_game:
                        logger.info(f"Match RENAMED: {server.match_name} -> {migrated_server.match_name}. Not counting.")
                        continue

            # 2. VALIDATION
            is_started = server.is_started
            has_enough_games = server.nb_game >= self.MIN_GAMES_THRESHOLD
            
            if is_started and has_enough_games:
                # 3. ATOMIC DB WRITE
                # Try to finish the match. DB constraint prevents double counting.
                counted = await self._try_finish_match(server, today)
                if counted:
                    finished_count += 1
                    logger.info(f"✅ COUNTED: {server.match_name} ({server.nb_game} games)")
                else:
                    logger.info(f"Received duplicate finish for {server.match_name} (already counted by another worker)")
            else:
                pass # Ignored (waiting or too short)

        self._previous_matches = current_matches
        return finished_count

    async def _try_finish_match(self, server: GameServer, date_obj: date) -> bool:
        """Atomically record finished match and update aggregates.

        Returns:
            True if match was newly counted, False if already existed.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                # 1. Clean the score and validate
                # We want to strip out intermediate game scores (e.g. ' -- 40:15' or ' -- 0:0*')
                # Examples: '6/4 5/4 -- 40:A*' -> '6/4 5/4', '0/0 -- 0:0' -> ''
                clean_score = server.score
                if " -- " in clean_score:
                    clean_score = clean_score.split(" -- ")[0].strip()
                
                # Check if it's an obviously unstarted or blank score (like '...' or '0/0')
                if not clean_score or clean_score == "..." or clean_score == "0/0":
                    logger.warning(f"Ignoring finished match {server.match_id} due to invalid score: '{server.score}'")
                    # We still return True to mark it 'processed/ignored' so we don't keep trying,
                    # but we don't insert it or count it. Actually returning False is better so
                    # we don't increment the API count either. But we don't want to retry it.
                    # Returning True essentially drops it safely since it's removed from previous_matches.
                    return False
                
                # Check for minimum games threshold (5)
                total_games = 0
                if clean_score:
                    sets = clean_score.split()
                    for s in sets:
                        if "/" in s:
                            parts = s.split("/")
                            g1_str = "".join(c for c in parts[0] if c.isdigit())
                            g2_str = "".join(c for c in parts[1].split("(")[0] if c.isdigit())
                            if g1_str and g2_str:
                                try:
                                    total_games += int(g1_str) + int(g2_str)
                                except ValueError:
                                    pass
                                    
                if total_games < 5:
                    logger.warning(f"Ignoring finished match {server.match_id} due to insufficient games ({total_games}): '{clean_score}'")
                    return False
                
                # Deduce winner from clean score
                deduced_winner = self._determine_winner(server.match_name, clean_score)
                
                # 2. Insert into finished_matches (Atomic Guard)
                match_record = FinishedMatch(
                    match_id=server.match_id,
                    date=date_obj,
                    match_name=server.match_name,
                    score=clean_score,
                    winner=deduced_winner,
                    p1_elo=server.elo,
                    p2_elo=server.other_elo
                )
                session.add(match_record)
                await session.flush() # Check constraints immediately
                
                # 2. Update Aggregates (Only if insert succeeded)
                mod = self._detect_mod(server)
                fmt = self._detect_format(server)
                
                # Ensure aggregate record exists
                await self._ensure_daily_record(session, date_obj)
                
                # Increment counters atomically using SQL expressions
                stmt = (
                    update(DailyStats)
                    .where(DailyStats.stats_date == date_obj)
                    .values({
                        getattr(DailyStats, f"{mod}_total"): getattr(DailyStats, f"{mod}_total") + 1,
                        getattr(DailyStats, f"{mod}_{fmt}"): getattr(DailyStats, f"{mod}_{fmt}") + 1
                    })
                )
                await session.execute(stmt)
                
                await session.commit()
                return True

            except IntegrityError:
                # Match ID already exists - ignore
                await session.rollback()
                return False
            except Exception as e:
                logger.error(f"Error finishing match {server.match_id}: {e}")
                await session.rollback()
                return False

    async def _ensure_daily_record(self, session, date_obj: date) -> None:
        """Ensure DailyStats record exists for today."""
        # Check existence first to avoid write locks if possible
        result = await session.execute(
            select(DailyStats.id).where(DailyStats.stats_date == date_obj)
        )
        if result.scalar_one_or_none():
            return

        # Try insert (ignore race conditions via ON CONFLICT DO NOTHING equivalent logic)
        try:
            # We can just attempt insert; if it fails due to unique constraint, that's fine
            session.add(DailyStats(stats_date=date_obj))
            await session.flush()
        except IntegrityError:
            # Another worker created it just now
            await session.rollback()

    async def save_to_db(self) -> None:
        """No-op for stateless service compatibility."""
        pass

    def _determine_winner(self, match_name: str, clean_score: str) -> str | None:
        """Deduce the winner based on match name and score string.
        
        Args:
            match_name: Format 'P1 vs P2'
            clean_score: Format '6/4 5/4'
            
        Returns:
            The winning player name, or None if indistinguishable.
        """
        if not clean_score or " vs " not in match_name:
            return None
            
        # Parse players
        p1, p2 = match_name.split(" vs ", 1)
        p1 = p1.strip()
        p2 = p2.strip()
        
        # Parse score
        # e.g. "6/4 5/4" -> ["6/4", "5/4"]
        sets = clean_score.split()
        
        p1_sets_won = 0
        p2_sets_won = 0
        p1_last_games = 0
        p2_last_games = 0
        
        for s in sets:
            if "/" not in s: 
                continue
            
            parts = s.split("/")
            
            # Clean non-digit chars (e.g. tiebreaks like "7/6(5)" -> 7, 6)
            g1_str = "".join(c for c in parts[0] if c.isdigit())
            g2_str = "".join(c for c in parts[1].split("(")[0] if c.isdigit())
            
            if not g1_str or not g2_str:
                continue
                
            try:
                g1 = int(g1_str)
                g2 = int(g2_str)
                
                if g1 > g2:
                    p1_sets_won += 1
                elif g2 > g1:
                    p2_sets_won += 1
                    
                p1_last_games = g1
                p2_last_games = g2
            except ValueError:
                continue
                
        # Determine winner
        if p1_sets_won > p2_sets_won:
            return p1
        elif p2_sets_won > p1_sets_won:
            return p2
        elif p1_sets_won == p2_sets_won:
            # If tied, verify the games of the final incomplete/played set (if they quit, who was leading?)
            if p1_last_games > p2_last_games:
                return p1
            elif p2_last_games > p1_last_games:
                return p2
                
        return None

    def get_today_stats(self) -> dict[str, Any]:
        """Legacy sync method - used by API.
        
        CAUTION: This should ideally be async, but the API endpoint calls it synchronously?
        Checking live_scores.py... no, it calls it sync.
        Wait, we need to change get_today_stats to be async or internal implementation uses sync engine?
        The codebase uses async SQLAlchemy.
        
        We must temporarily return an empty/default structure here if called synchronously,
        OR refactor the endpoint to be async and call an async version of this.
        
        Looking at live_scores.py:
        @router.get("/stats/today")
        async def get_today_stats() -> dict:
            ...
            return stats_service.get_today_stats()
            
        The ROUTER is async, but it calls a sync method on the service.
        We need to make this method async or use a run_until_complete hack (bad).
        
        Since we are refactoring, we SHOULD change the API endpoint to await this method.
        But for now, to avoid breaking the signature contract if we can't change specific files, 
        we might be stuck. 
        
        However, the user asked to FIX concurrency. 
        We will implement `async def get_today_stats_async` and then we MUST update live_scores.py endpoint.
        """
        # Return empty/placeholder if called synchronously
        # Real impl needs async
        return {
            "date": datetime.now().date().isoformat(),
            "xkt": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
            "wtsl": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
            "vanilla": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
            "note": "Please update API to use await get_today_stats_async()"
        }

    async def get_today_stats_async(self) -> dict[str, Any]:
        """Get current day's stats from DB."""
        today = self._get_today()
        session_factory = get_session_factory()
        
        try:
            async with session_factory() as session:
                result = await session.execute(
                    select(DailyStats).where(DailyStats.stats_date == today)
                )
                record = result.scalar_one_or_none()
                
                if record:
                    return record.to_dict()
                
                # If no record yet, return zeros
                return {
                    "date": today.isoformat(),
                    "xkt": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
                    "wtsl": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
                    "vanilla": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
                }
        except Exception as e:
            logger.error(f"Failed to fetch today's stats: {e}")
            return {}

    async def get_history(self, days: int = 7) -> list[dict[str, Any]]:
        """Get stats history for the last N days."""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(DailyStats)
                    .order_by(DailyStats.stats_date.desc())
                    .limit(days)
                )
                records = result.scalars().all()
                return [r.to_dict() for r in records]
        except Exception as e:
            logger.error(f"Failed to get stats history: {e}")
            return []

    async def get_monthly_stats_async(self, time_range: str = "this_month") -> dict[str, Any]:
        """Get average stats for the specified time range."""
        today = self._get_today()
        
        if time_range == "last_month":
            # first day of this month
            first_day_this_month = date(today.year, today.month, 1)
            # last day of last month
            end_date = first_day_this_month - timedelta(days=1)
            # first day of last month
            start_date = date(end_date.year, end_date.month, 1)
        elif time_range == "year":
            start_date = date(today.year, 1, 1)
            end_date = today
        else: # "this_month"
            start_date = date(today.year, today.month, 1)
            end_date = today
        
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(DailyStats)
                    .where(DailyStats.stats_date >= start_date)
                    .where(DailyStats.stats_date <= end_date)
                )
                records = result.scalars().all()
                
                if not records:
                    return {
                        "date_range": f"{start_date.isoformat()} to {end_date.isoformat()}",
                        "days_recorded": 0,
                        "xkt": {"avg_total": 0, "avg_bo1": 0, "avg_bo3": 0, "avg_bo5": 0},
                        "wtsl": {"avg_total": 0, "avg_bo1": 0, "avg_bo3": 0, "avg_bo5": 0},
                        "vanilla": {"avg_total": 0, "avg_bo1": 0, "avg_bo3": 0, "avg_bo5": 0},
                    }
                
                days_count = len(records)
                
                def avg(vals: list[int]) -> int:
                    return sum(vals) // days_count
                    
                return {
                    "date_range": f"{start_date.isoformat()} to {end_date.isoformat()}",
                    "days_recorded": days_count,
                    "xkt": {
                        "avg_total": avg([r.xkt_total for r in records]),
                        "avg_bo1": avg([r.xkt_bo1 for r in records]),
                        "avg_bo3": avg([r.xkt_bo3 for r in records]),
                        "avg_bo5": avg([r.xkt_bo5 for r in records]),
                    },
                    "wtsl": {
                        "avg_total": avg([r.wtsl_total for r in records]),
                        "avg_bo1": avg([r.wtsl_bo1 for r in records]),
                        "avg_bo3": avg([r.wtsl_bo3 for r in records]),
                        "avg_bo5": avg([r.wtsl_bo5 for r in records]),
                    },
                    "vanilla": {
                        "avg_total": avg([r.vanilla_total for r in records]),
                        "avg_bo1": avg([r.vanilla_bo1 for r in records]),
                        "avg_bo3": avg([r.vanilla_bo3 for r in records]),
                        "avg_bo5": avg([r.vanilla_bo5 for r in records]),
                    },
                }
        except Exception as e:
            logger.error(f"Failed to fetch monthly stats: {e}")
            return {}

    async def _load_alias_map(self) -> dict[str, str]:
        """Load alias->canonical_name map from DB (all lowercase keys)."""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(select(PlayerAlias))
                aliases = result.scalars().all()
                return {a.alias: a.canonical_name for a in aliases}
        except Exception as e:
            logger.error(f"Failed to load alias map: {e}")
            return {}

    def _resolve_name(self, name: str, alias_map: dict[str, str]) -> str:
        """Resolve a player name through the alias map (case-insensitive)."""
        return alias_map.get(name.lower(), name)

    async def get_top_players_async(self, limit: int = 5, time_range: str = "this_month") -> list[dict[str, Any]]:
        """Get the top players with most matches in the specified time range."""
        today = self._get_today()
        
        if time_range == "last_month":
            first_day_this_month = date(today.year, today.month, 1)
            end_date = first_day_this_month - timedelta(days=1)
            start_date = date(end_date.year, end_date.month, 1)
        elif time_range == "year":
            start_date = date(today.year, 1, 1)
            end_date = today
        else: # "this_month"
            start_date = date(today.year, today.month, 1)
            end_date = today
        
        try:
            alias_map = await self._load_alias_map()
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(FinishedMatch.match_name, FinishedMatch.p1_elo, FinishedMatch.p2_elo, FinishedMatch.score)
                    .where(FinishedMatch.date >= start_date)
                    .where(FinishedMatch.date <= end_date)
                    .order_by(FinishedMatch.created_at.asc())
                )
                match_records = result.all()
                
                from collections import Counter
                player_counts = Counter()
                player_latest_elo = {}
                
                for row in match_records:
                    name = row.match_name
                    p1_elo = row.p1_elo
                    p2_elo = row.p2_elo
                    
                    if not name:
                        continue
                        
                    # Filter out matches with less than 5 games
                    total_games = 0
                    if row.score:
                        sets = row.score.split()
                        for s in sets:
                            if "/" in s:
                                parts = s.split("/")
                                g1_str = "".join(c for c in parts[0] if c.isdigit())
                                g2_str = "".join(c for c in parts[1].split("(")[0] if c.isdigit())
                                if g1_str and g2_str:
                                    try:
                                        total_games += int(g1_str) + int(g2_str)
                                    except ValueError:
                                        pass
                    if total_games < 5:
                        continue
                        
                    if " vs " in name:
                        p1, p2 = name.split(" vs ", 1)
                        p1, p2 = self._resolve_name(p1.strip(), alias_map), self._resolve_name(p2.strip(), alias_map)
                        if p1 and p1 != "Unknown" and p1 != "1210967164" and not p1.startswith("[."):
                            player_counts[p1] += 1
                            if p1_elo is not None and p1_elo > 0:
                                player_latest_elo[p1] = p1_elo
                        if p2 and p2 != "Unknown" and p2 != "1210967164" and not p2.startswith("[."):
                            player_counts[p2] += 1
                            if p2_elo is not None and p2_elo > 0:
                                player_latest_elo[p2] = p2_elo
                    else:
                        resolved = self._resolve_name(name.strip(), alias_map)
                        if resolved and resolved != "Unknown" and resolved != "1210967164" and not resolved.startswith("[."):
                            player_counts[resolved] += 1
                            if p1_elo is not None and p1_elo > 0:
                                player_latest_elo[resolved] = p1_elo
                
                top_players = player_counts.most_common(limit)
                
                return [
                    {"name": name, "matches": count, "latest_elo": player_latest_elo.get(name)}
                    for name, count in top_players
                ]
                
        except Exception as e:
            logger.error(f"Failed to fetch top players: {e}")
            return []

    async def get_all_players_async(self) -> list[dict[str, Any]]:
        """Get all players ever recorded with their latest ELO, total matches, and last match date."""
        try:
            alias_map = await self._load_alias_map()
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(
                        FinishedMatch.match_name,
                        FinishedMatch.p1_elo,
                        FinishedMatch.p2_elo,
                        FinishedMatch.date,
                        FinishedMatch.score,
                    )
                    .order_by(FinishedMatch.created_at.asc())
                )
                match_records = result.all()

                from collections import Counter

                player_counts: Counter[str] = Counter()
                player_latest_elo: dict[str, int] = {}
                player_last_date: dict[str, date] = {}

                for row in match_records:
                    name = row.match_name
                    p1_elo = row.p1_elo
                    p2_elo = row.p2_elo
                    match_date = row.date

                    if not name:
                        continue
                        
                    # Filter out matches with less than 5 games
                    total_games = 0
                    if row.score:
                        sets = row.score.split()
                        for s in sets:
                            if "/" in s:
                                parts = s.split("/")
                                g1_str = "".join(c for c in parts[0] if c.isdigit())
                                g2_str = "".join(c for c in parts[1].split("(")[0] if c.isdigit())
                                if g1_str and g2_str:
                                    try:
                                        total_games += int(g1_str) + int(g2_str)
                                    except ValueError:
                                        pass
                    if total_games < 5:
                        continue

                    if " vs " in name:
                        p1, p2 = name.split(" vs ", 1)
                        p1, p2 = self._resolve_name(p1.strip(), alias_map), self._resolve_name(p2.strip(), alias_map)

                        if p1 and p1 != "Unknown" and p1 != "1210967164" and not p1.startswith("[."):
                            player_counts[p1] += 1
                            if p1_elo is not None and p1_elo > 0:
                                player_latest_elo[p1] = p1_elo
                            if match_date:
                                player_last_date[p1] = match_date

                        if p2 and p2 != "Unknown" and p2 != "1210967164" and not p2.startswith("[."):
                            player_counts[p2] += 1
                            if p2_elo is not None and p2_elo > 0:
                                player_latest_elo[p2] = p2_elo
                            if match_date:
                                player_last_date[p2] = match_date
                    else:
                        resolved = self._resolve_name(name.strip(), alias_map)
                        if resolved and resolved != "Unknown" and resolved != "1210967164" and not resolved.startswith("[."):
                            player_counts[resolved] += 1
                            if p1_elo is not None and p1_elo > 0:
                                player_latest_elo[resolved] = p1_elo
                            if match_date:
                                player_last_date[resolved] = match_date

                return [
                    {
                        "name": name,
                        "total_matches": count,
                        "latest_elo": player_latest_elo.get(name),
                        "last_match_date": player_last_date.get(name, "").isoformat() if player_last_date.get(name) else None,
                    }
                    for name, count in player_counts.most_common()
                ]

        except Exception as e:
            logger.error(f"Failed to fetch all players: {e}")
            return []

    async def get_player_details_async(self, player_name: str) -> dict[str, Any]:
        """Get detailed match history and stats for a specific player.

        Returns matches played, wins, losses, best win (highest ELO opponent beaten),
        worst loss, and recent activity counts.
        """
        try:
            alias_map = await self._load_alias_map()
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(
                        FinishedMatch.match_name,
                        FinishedMatch.score,
                        FinishedMatch.winner,
                        FinishedMatch.p1_elo,
                        FinishedMatch.p2_elo,
                        FinishedMatch.date,
                    )
                    .order_by(FinishedMatch.date.desc())
                )
                all_matches = result.all()

                # Resolve which names map to this player
                target_lower = player_name.lower()
                # Build set of raw names that resolve to this player
                raw_names_for_player: set[str] = {target_lower}
                for alias_lower, canonical in alias_map.items():
                    if canonical.lower() == target_lower or alias_lower == target_lower:
                        raw_names_for_player.add(alias_lower)
                        raw_names_for_player.add(canonical.lower())

                today = self._get_today()
                week_ago = today - timedelta(days=7)
                month_ago = today - timedelta(days=30)

                matches: list[dict[str, Any]] = []
                wins = 0
                losses = 0
                best_win: dict[str, Any] | None = None
                worst_loss: dict[str, Any] | None = None
                matches_last_7 = 0
                matches_last_30 = 0

                for row in all_matches:
                    name = row.match_name
                    if not name or " vs " not in name:
                        continue

                    raw_p1, raw_p2 = name.split(" vs ", 1)
                    p1 = self._resolve_name(raw_p1.strip(), alias_map)
                    p2 = self._resolve_name(raw_p2.strip(), alias_map)

                    # Check if this player is involved
                    is_p1 = p1.lower() in raw_names_for_player
                    is_p2 = p2.lower() in raw_names_for_player
                    if not is_p1 and not is_p2:
                        continue

                    # Calculate total games played to filter out aborted matches
                    total_games = 0
                    if row.score:
                        sets = row.score.split()
                        for s in sets:
                            if "/" in s:
                                parts = s.split("/")
                                g1_str = "".join(c for c in parts[0] if c.isdigit())
                                g2_str = "".join(c for c in parts[1].split("(")[0] if c.isdigit())
                                if g1_str and g2_str:
                                    try:
                                        total_games += int(g1_str) + int(g2_str)
                                    except ValueError:
                                        pass
                                        
                    # Ignore matches with less than 5 games (aborted early)
                    if total_games < 5:
                        continue

                    opponent = p2 if is_p1 else p1
                    player_elo = row.p1_elo if is_p1 else row.p2_elo
                    opponent_elo = row.p2_elo if is_p1 else row.p1_elo

                    winner_resolved = None
                    if row.winner:
                        winner_resolved = self._resolve_name(row.winner.strip(), alias_map)

                    did_win = winner_resolved and winner_resolved.lower() in raw_names_for_player
                    did_lose = winner_resolved and not did_win and winner_resolved.strip() != ""

                    match_entry = {
                        "opponent": opponent,
                        "score": row.score,
                        "date": row.date.isoformat() if row.date else None,
                        "player_elo": player_elo,
                        "opponent_elo": opponent_elo,
                        "result": "W" if did_win else ("L" if did_lose else "?"),
                    }
                    matches.append(match_entry)

                    if did_win:
                        wins += 1
                        if opponent_elo and opponent_elo > 0:
                            if best_win is None or opponent_elo > (best_win.get("opponent_elo") or 0):
                                best_win = match_entry
                    elif did_lose:
                        losses += 1
                        if opponent_elo and opponent_elo > 0:
                            if worst_loss is None or opponent_elo < (worst_loss.get("opponent_elo") or 9999):
                                worst_loss = match_entry

                    if row.date:
                        if row.date >= week_ago:
                            matches_last_7 += 1
                        if row.date >= month_ago:
                            matches_last_30 += 1

                completed_matches = wins + losses
                return {
                    "name": player_name,
                    "total_matches": completed_matches,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(wins / completed_matches * 100, 1) if completed_matches > 0 else 0,
                    "matches_last_7_days": matches_last_7,
                    "matches_last_30_days": matches_last_30,
                    "best_win": best_win,
                    "worst_loss": worst_loss,
                    "recent_matches": matches[:10],  # Last 10 matches
                }

        except Exception as e:
            logger.error(f"Failed to fetch player details for {player_name}: {e}")
            return {"name": player_name, "error": str(e)}


# Singleton instance
_stats_service: StatsService | None = None


def get_stats_service() -> StatsService:
    """Get the stats service singleton."""
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService()
    return _stats_service
