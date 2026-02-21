"""Stats tracking service.

Tracks finished matches (5+ games) and persists daily statistics.
Stateless implementation relying on Database for concurrency safety.
"""

import re
from datetime import date, datetime
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
                
                # Deduce winner from clean score
                deduced_winner = self._determine_winner(server.match_name, clean_score)
                
                # 2. Insert into finished_matches (Atomic Guard)
                match_record = FinishedMatch(
                    match_id=server.match_id,
                    date=date_obj,
                    match_name=server.match_name,
                    score=clean_score,
                    winner=deduced_winner
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

    async def get_monthly_stats_async(self) -> dict[str, Any]:
        """Get average stats for the current month."""
        today = self._get_today()
        # First day of the current month
        start_of_month = date(today.year, today.month, 1)
        
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(DailyStats)
                    .where(DailyStats.stats_date >= start_of_month)
                    .where(DailyStats.stats_date <= today)
                )
                records = result.scalars().all()
                
                if not records:
                    return {
                        "date_range": f"{start_of_month.isoformat()} to {today.isoformat()}",
                        "days_recorded": 0,
                        "xkt": {"avg_total": 0, "avg_bo1": 0, "avg_bo3": 0, "avg_bo5": 0},
                        "wtsl": {"avg_total": 0, "avg_bo1": 0, "avg_bo3": 0, "avg_bo5": 0},
                        "vanilla": {"avg_total": 0, "avg_bo1": 0, "avg_bo3": 0, "avg_bo5": 0},
                    }
                
                days_count = len(records)
                
                def avg(vals: list[int]) -> int:
                    return sum(vals) // days_count
                    
                return {
                    "date_range": f"{start_of_month.isoformat()} to {today.isoformat()}",
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

    async def get_top_players_async(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get the top players with most matches in the current month."""
        today = self._get_today()
        start_of_month = date(today.year, today.month, 1)
        
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Optimized query: only fetch match names
                result = await session.execute(
                    select(FinishedMatch.match_name)
                    .where(FinishedMatch.date >= start_of_month)
                    .where(FinishedMatch.date <= today)
                )
                match_names = result.scalars().all()
                
                # Manual parsing: match_name is typically "Player1 vs Player2"
                from collections import Counter
                player_counts = Counter()
                
                for name in match_names:
                    if not name:
                        continue
                    if " vs " in name:
                        p1, p2 = name.split(" vs ", 1)
                        p1, p2 = p1.strip(), p2.strip()
                        if p1 and p1 != "Unknown" and p1 != "1210967164":
                            player_counts[p1] += 1
                        if p2 and p2 != "Unknown" and p2 != "1210967164":
                            player_counts[p2] += 1
                    else:
                        # Sometimes match_name is just "Player1" or weird string
                        name = name.strip()
                        if name and name != "Unknown" and name != "1210967164":
                            player_counts[name] += 1
                
                top_players = player_counts.most_common(limit)
                
                return [
                    {"name": name, "matches": count}
                    for name, count in top_players
                ]
                
        except Exception as e:
            logger.error(f"Failed to fetch top players: {e}")
            return []


# Singleton instance
_stats_service: StatsService | None = None


def get_stats_service() -> StatsService:
    """Get the stats service singleton."""
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService()
    return _stats_service
