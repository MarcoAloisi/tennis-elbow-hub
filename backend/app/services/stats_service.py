"""Stats tracking service.

Tracks finished matches (5+ games) and persists daily statistics.
Uses in-memory tracking with periodic DB checkpoints for performance.
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.logging import get_logger
from app.models.daily_stats import DailyStats
from app.models.finished_match import FinishedMatch
from app.models.game_server import GameServer

logger = get_logger("stats_service")


class StatsService:
    """Service for tracking and persisting match statistics."""

    # Minimum games required to count a match as "played"
    MIN_GAMES_THRESHOLD = 5

    def __init__(self) -> None:
        """Initialize the stats service."""
        self.settings = get_settings()
        self.timezone = ZoneInfo(self.settings.stats_timezone)

        # In-memory tracking
        self._previous_matches: dict[str, GameServer] = {}  # match_id -> server
        self._counted_match_ids: set[str] = set()  # Already counted match IDs
        self._today_stats: dict[str, dict[str, int]] = self._empty_stats()
        self._current_date: date | None = None
        self._dirty = False  # True if in-memory stats differ from DB
        
        # Initial load will happen on first track_matches call if needed

    def _empty_stats(self) -> dict[str, dict[str, int]]:
        """Return empty stats structure."""
        return {
            "xkt": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
            "wtsl": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
            "vanilla": {"total": 0, "bo1": 0, "bo3": 0, "bo5": 0},
        }

    def _get_today(self) -> date:
        """Get current date in configured timezone."""
        return datetime.now(self.timezone).date()

    def _detect_mod(self, server: GameServer) -> str:
        """Detect mod type from server tag_line."""
        tag = (server.tag_line or "").lower()
        # Check WTSL first - handles "XKT(WTSL)" format
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

        # Check for day rollover or initial load
        if self._current_date != today:
            if self._dirty and self._current_date is not None:
                await self.save_to_db()
            
            self._current_date = today
            self._today_stats = self._empty_stats()
            self._previous_matches.clear()
            self._counted_match_ids.clear()
            
            await self._load_from_db(today)

        # Build current matches dict using match_id
        current_matches = {s.match_id: s for s in current_servers}

        logger.debug(
            f"[STATS] Tracking: {len(current_matches)} current, "
            f"{len(self._previous_matches)} previous, "
            f"{len(self._counted_match_ids)} already counted today"
        )
        
        # Identify potentially finished and new matches
        previous_ids = set(self._previous_matches.keys())
        current_ids = set(current_matches.keys())
        
        missing_ids = previous_ids - current_ids
        new_ids = current_ids - previous_ids
        
        # Helper to generate a robust identity key for finding renames
        def _get_identity_key(s: GameServer) -> tuple:
            return (
                s.creation_time_ms,
                s.port,
                s.surface_name,
                s.game_info.nb_set,
                s.game_info.player_config,
            )
        
        # Index new matches by identity key
        new_matches_by_identity = {
            _get_identity_key(current_matches[mid]): mid
            for mid in new_ids
        }

        # Find finished matches (in previous but not in current)
        finished_count = 0
        for match_id in missing_ids:
            server = self._previous_matches[match_id]
            
            # CHECK FOR RENAME / MIGRATION
            # 1. Check invariants (Time, Port, Surface, Mode)
            identity_key = _get_identity_key(server)
            migrated_id = new_matches_by_identity.get(identity_key)
            
            if migrated_id:
                migrated_server = current_matches[migrated_id]
                
                # 2. Check Player Overlap (The User's Idea!)
                # If matches are truly the same (just renamed), at least one player should persist.
                # If NO players overlap, it's likely a new match on the same server instance.
                # We normalize names to be safe.
                p1_names = {n.lower().strip() for n in server.player_names if n != "Unknown"}
                p2_names = {n.lower().strip() for n in migrated_server.player_names if n != "Unknown"}
                
                # Special case: If old match was "Waiting", treat it as the ancestor of the new match
                # This ensures we log a clean "RENAMED" transition from Waiting -> Real Match
                is_p1_waiting = not p1_names or "waiting" in p1_names
                
                has_overlap = is_p1_waiting or not p2_names or bool(p1_names & p2_names)
                
                if has_overlap:
                    # Additional sanity check: Games shouldn't decrease significantly
                    if migrated_server.nb_game >= server.nb_game:
                        logger.info(
                            f"[STATS] 🔄 Match RENAMED: {server.match_name} -> {migrated_server.match_name} "
                            f"(ID: {match_id} -> {migrated_id}). NOT counting as finished."
                        )
                        continue  # Skip counting, handover to new ID
                else:
                    logger.info(
                        f"[STATS] ⚠️ Identity collision but NEW players: "
                        f"{server.player_names} vs {migrated_server.player_names}. "
                        f"Treating as separate finished match."
                    )
            
            # Match actually gone - log why we're counting or not
            
            # Check criteria
            is_started = server.is_started
            has_enough_games = server.nb_game >= self.MIN_GAMES_THRESHOLD
            not_counted = match_id not in self._counted_match_ids
            
            if is_started and has_enough_games and not_counted:
                # VALID FINISHED MATCH
                self._record_match_stats(server)
                await self._persist_finished_match(server, today)
                
                self._counted_match_ids.add(match_id)
                finished_count += 1
                
                await self.save_to_db()
                
                logger.info(
                    f"[STATS] ✅ COUNTED: {server.match_name} "
                    f"({server.nb_game} games, {self._detect_mod(server)}, {self._detect_format(server)})"
                )
            else:
                # Log SKIP reason
                reason = []
                if not is_started:
                    reason.append("was WAITING")
                if not has_enough_games:
                    reason.append(f"only {server.nb_game} games")
                if not not_counted:
                    reason.append("already counted")
                
                logger.info(f"[STATS] ❌ SKIPPED: {server.match_name} - {', '.join(reason)}")

        # Update previous for next comparison
        self._previous_matches = current_matches

        return finished_count

    def _record_match_stats(self, server: GameServer) -> None:
        """Record a finished match in memory stats aggregates."""
        mod = self._detect_mod(server)
        fmt = self._detect_format(server)

        self._today_stats[mod]["total"] += 1
        self._today_stats[mod][fmt] += 1
        self._dirty = True

    async def _persist_finished_match(self, server: GameServer, date_obj: date) -> None:
        """Save individual finished match to DB."""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                match_record = FinishedMatch(
                    match_id=server.match_id,
                    date=date_obj,
                    match_name=server.match_name,
                    score=server.score,
                    winner=None,  # We don't parse winner here yet
                )
                session.add(match_record)
                await session.commit()
                logger.debug(f"Persisted finished match {server.match_id}")
        except Exception as e:
            logger.error(f"Failed to persist finished match {server.match_id}: {e}")

    async def _load_from_db(self, target_date: date) -> None:
        """Load existing stats and counted IDs from DB for a given date."""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # 1. Load Aggregates (DailyStats)
                result = await session.execute(
                    select(DailyStats).where(DailyStats.stats_date == target_date)
                )
                record = result.scalar_one_or_none()

                if record:
                    self._today_stats = record.to_dict()
                    self._today_stats.pop("date", None)
                    logger.info(f"Loaded existing aggregates for {target_date}")
                else:
                    logger.info(f"No existing aggregates for {target_date}")

                # 2. Load Counted Match IDs (FinishedMatch)
                result_ids = await session.execute(
                    select(FinishedMatch.match_id).where(FinishedMatch.date == target_date)
                )
                existing_ids = result_ids.scalars().all()
                self._counted_match_ids = set(existing_ids)
                logger.info(f"Loaded {len(self._counted_match_ids)} finished match IDs for {target_date}")

        except Exception as e:
            logger.error(f"Failed to load stats from DB: {e}")

    async def save_to_db(self) -> None:
        """Save current in-memory stats aggregates to database."""
        if not self._dirty or self._current_date is None:
            return

        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Upsert DailyStats
                result = await session.execute(
                    select(DailyStats).where(
                        DailyStats.stats_date == self._current_date
                    )
                )
                record = result.scalar_one_or_none()

                if record is None:
                    record = DailyStats(stats_date=self._current_date)
                    session.add(record)

                # Update all fields
                stats = self._today_stats
                record.xkt_total = stats["xkt"]["total"]
                record.xkt_bo1 = stats["xkt"]["bo1"]
                record.xkt_bo3 = stats["xkt"]["bo3"]
                record.xkt_bo5 = stats["xkt"]["bo5"]

                record.wtsl_total = stats["wtsl"]["total"]
                record.wtsl_bo1 = stats["wtsl"]["bo1"]
                record.wtsl_bo3 = stats["wtsl"]["bo3"]
                record.wtsl_bo5 = stats["wtsl"]["bo5"]

                record.vanilla_total = stats["vanilla"]["total"]
                record.vanilla_bo1 = stats["vanilla"]["bo1"]
                record.vanilla_bo3 = stats["vanilla"]["bo3"]
                record.vanilla_bo5 = stats["vanilla"]["bo5"]

                await session.commit()
                self._dirty = False
                logger.info(f"Saved stats aggregates to DB for {self._current_date}")

        except Exception as e:
            logger.error(f"Failed to save stats to DB: {e}")

    def get_today_stats(self) -> dict[str, Any]:
        """Get current day's stats."""
        return {
            "date": self._current_date.isoformat() if self._current_date else None,
            **self._today_stats,
        }

    async def get_history(self, days: int = 7) -> list[dict[str, Any]]:
        """Get stats history for the last N days.

        Args:
            days: Number of days to retrieve.

        Returns:
            List of daily stats dictionaries.
        """
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


# Singleton instance
_stats_service: StatsService | None = None


def get_stats_service() -> StatsService:
    """Get the stats service singleton."""
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService()
    return _stats_service
