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
        self._counted_match_ids: set[str] = set()  # Already counted match IDs (prevents duplicates)
        self._today_stats: dict[str, dict[str, int]] = self._empty_stats()
        self._current_date: date | None = None
        self._dirty = False  # True if in-memory stats differ from DB

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
        if "xkt" in tag:
            return "xkt"
        elif "wtsl" in tag:
            return "wtsl"
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

        # Check for day rollover
        if self._current_date != today:
            if self._dirty and self._current_date is not None:
                await self.save_to_db()
            self._today_stats = self._empty_stats()
            self._current_date = today
            self._previous_matches.clear()
            self._counted_match_ids.clear()  # Reset counted matches for new day
            await self._load_from_db(today)

        # Build current matches dict using match_id
        current_matches = {s.match_id: s for s in current_servers}

        # Find finished matches (in previous but not in current)
        finished_count = 0
        for match_id, server in self._previous_matches.items():
            if match_id not in current_matches:
                # Match finished - check if it had enough games AND wasn't already counted
                if server.nb_game >= self.MIN_GAMES_THRESHOLD and match_id not in self._counted_match_ids:
                    self._record_match(server)
                    self._counted_match_ids.add(match_id)  # Mark as counted
                    finished_count += 1
                    await self.save_to_db()  # PERSIST IMMEDIATELY
                    logger.info(
                        f"Match finished: {server.match_name} "
                        f"({server.nb_game} games, {self._detect_mod(server)})"
                    )

        # Update previous for next comparison
        self._previous_matches = current_matches

        return finished_count

    def _record_match(self, server: GameServer) -> None:
        """Record a finished match in memory stats."""
        mod = self._detect_mod(server)
        fmt = self._detect_format(server)

        self._today_stats[mod]["total"] += 1
        self._today_stats[mod][fmt] += 1
        self._dirty = True

    async def _load_from_db(self, target_date: date) -> None:
        """Load existing stats from DB for a given date."""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(DailyStats).where(DailyStats.stats_date == target_date)
                )
                record = result.scalar_one_or_none()

                if record:
                    self._today_stats = record.to_dict()
                    # Remove date key from the dict (it's not part of stats structure)
                    self._today_stats.pop("date", None)
                    logger.info(f"Loaded existing stats for {target_date}")
                else:
                    logger.info(f"No existing stats for {target_date}, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load stats from DB: {e}")

    async def save_to_db(self) -> None:
        """Save current in-memory stats to database."""
        if not self._dirty or self._current_date is None:
            return

        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Upsert: find existing or create new
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
                logger.info(f"Saved stats to DB for {self._current_date}")

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
