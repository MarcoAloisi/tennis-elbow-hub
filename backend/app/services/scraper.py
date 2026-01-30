"""Scraper service for fetching live tennis scores.

This module handles HTTP requests to the score source URL
and manages the data fetching lifecycle.
"""

from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.game_server import GameServer, GameServerList
from app.services.parser import parse_server_data

logger = get_logger("scraper")


class ScraperService:
    """Service for fetching and parsing live tennis scores."""

    def __init__(self) -> None:
        """Initialize the scraper service."""
        self.settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            Async HTTP client instance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers={
                    "User-Agent": "TennisTracker/1.0",
                    "Accept": "text/plain, */*",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def fetch_raw_data(self) -> str | None:
        """Fetch raw score data from the configured URL.

        Returns:
            Raw response text or None if fetch fails.
        """
        url = self.settings.live_scores_url
        if not url:
            logger.warning("Live scores URL not configured")
            return None

        try:
            client = await self.get_client()
            response = await client.get(url)
            response.raise_for_status()

            logger.info(f"Fetched data from {url}: {len(response.text)} chars")
            return response.text

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching data from {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} from {url}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching from {url}: {e}")
            return None

    async def fetch_servers(self, track_stats: bool = True) -> GameServerList:
        """Fetch and parse live server data.

        Args:
            track_stats: Whether to track finished matches for stats.

        Returns:
            GameServerList containing parsed servers.
        """
        raw_data = await self.fetch_raw_data()

        servers: list[GameServer] = []
        if raw_data:
            servers = list(parse_server_data(raw_data))
            logger.info(f"Parsed {len(servers)} servers")

        # Track finished matches for stats
        if track_stats and servers:
            from app.services.stats_service import get_stats_service

            stats_service = get_stats_service()
            finished = await stats_service.track_matches(servers)
            if finished > 0:
                logger.info(f"Detected {finished} finished matches")

        return GameServerList(
            servers=servers,
            total=len(servers),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def fetch_servers_filtered(
        self,
        *,
        surface: str | None = None,
        started_only: bool = False,
        min_elo: int | None = None,
        max_elo: int | None = None,
    ) -> GameServerList:
        """Fetch servers with optional filters.

        Args:
            surface: Filter by surface name (case-insensitive).
            started_only: Only return started matches.
            min_elo: Minimum Elo rating filter.
            max_elo: Maximum Elo rating filter.

        Returns:
            Filtered GameServerList.
        """
        result = await self.fetch_servers()

        filtered = result.servers

        # Apply filters
        if started_only:
            filtered = [s for s in filtered if s.is_started]

        if surface:
            surface_lower = surface.lower()
            filtered = [s for s in filtered if surface_lower in s.surface_name.lower()]

        if min_elo is not None:
            filtered = [s for s in filtered if s.elo >= min_elo]

        if max_elo is not None:
            filtered = [s for s in filtered if s.elo <= max_elo]

        return GameServerList(
            servers=filtered,
            total=len(filtered),
            timestamp=result.timestamp,
        )


# Singleton instance
_scraper_service: ScraperService | None = None


def get_scraper_service() -> ScraperService:
    """Get the scraper service singleton.

    Returns:
        ScraperService instance.
    """
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service
