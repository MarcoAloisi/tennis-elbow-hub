"""Live scores API endpoints.

Provides REST and WebSocket endpoints for fetching live tennis match scores.
"""

import asyncio
import time
from typing import Annotated
from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect, status

from app.api.deps import ScraperDep, SettingsDep
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.models.game_server import GameServerList

logger = get_logger("api.live_scores")
router = APIRouter(prefix="/scores", tags=["Live Scores"])


@router.get(
    "",
    response_model=GameServerList,
    summary="Get live scores",
    description="Fetch current live tennis match scores from the configured source.",
)
@limiter.limit("60/minute")
async def get_live_scores(
    request: Request,
    scraper: ScraperDep,
    surface: Annotated[str | None, Query(description="Filter by surface")] = None,
    started_only: Annotated[
        bool, Query(description="Only show started matches")
    ] = False,
    min_elo: Annotated[int | None, Query(ge=0, description="Minimum Elo")] = None,
    max_elo: Annotated[int | None, Query(ge=0, description="Maximum Elo")] = None,
) -> GameServerList:
    """Get current live scores with optional filters.

    Args:
        request: FastAPI Request (required for rate limiting).
        scraper: Injected scraper service.
        surface: Filter by court surface name.
        started_only: Only return started matches.
        min_elo: Minimum Elo rating filter.
        max_elo: Maximum Elo rating filter.

    Returns:
        List of game servers matching the filters.
    """
    return await scraper.fetch_servers_filtered(
        surface=surface,
        started_only=started_only,
        min_elo=min_elo,
        max_elo=max_elo,
    )


@router.get(
    "/stats/today",
    summary="Get today's finished match stats",
    description="Get aggregated statistics for matches finished today.",
)
@limiter.limit("60/minute")
async def get_today_stats(request: Request) -> dict:
    """Get today's finished match statistics.

    Returns:
        Today's stats by mod and format.
    """
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_today_stats_async()


@router.get(
    "/stats/history",
    summary="Get historical stats",
    description="Get daily stats for the last N days.",
)
@limiter.limit("60/minute")
async def get_stats_history(
    request: Request,
    days: Annotated[int, Query(ge=1, le=90, description="Number of days")] = 7,
) -> list[dict]:
    """Get historical daily statistics.

    Args:
        request: FastAPI Request (required for rate limiting).
        days: Number of days to retrieve (1-90).

    Returns:
        List of daily stats.
    """
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_history(days)


@router.get(
    "/stats/monthly",
    summary="Get monthly stats averages",
    description="Get daily average statistics for the specified time range.",
)
@limiter.limit("60/minute")
async def get_monthly_stats(
    request: Request,
    time_range: Annotated[str, Query(description="Time range filter (this_month, last_month, year)")] = "this_month",
) -> dict:
    """Get monthly average statistics.

    Returns:
        Average daily stats for the specified time range.
    """
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_monthly_stats_async(time_range=time_range)


@router.get(
    "/stats/top-players",
    summary="Get top players by time range",
    description="Get the top players with the most matches in the specified time range.",
)
@limiter.limit("60/minute")
async def get_top_players(
    request: Request,
    time_range: Annotated[str, Query(description="Time range filter (this_month, last_month, year)")] = "this_month",
) -> list[dict]:
    """Get top players for the specified time range.

    Returns:
        List of players and their match counts.
    """
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_top_players_async(limit=5, time_range=time_range)


@router.get(
    "/h2h",
    summary="Get head-to-head breakdown for two players",
    description="Get the head-to-head record and recent form behind a live match's win probability. Public — no login required, this is match-level info, not personal player stats.",
)
@limiter.limit("30/minute")
async def get_h2h(
    request: Request,
    player_a: Annotated[str, Query(min_length=1, description="First player's name")],
    player_b: Annotated[str, Query(min_length=1, description="Second player's name")],
    surface: Annotated[str | None, Query(description="This match's surface, for a surface-specific H2H breakdown")] = None,
    mod: Annotated[str | None, Query(description="This match's mod, for a mod-specific H2H breakdown")] = None,
) -> dict:
    """Get head-to-head record and recent form for two players.

    Args:
        request: FastAPI Request (required for rate limiting).
        player_a: First player's name.
        player_b: Second player's name.
        surface: Optional surface filter for a surface-specific H2H breakdown.
        mod: Optional mod filter for a mod-specific H2H breakdown.

    Returns:
        H2H record (overall + surface/mod-specific) and each player's
        recent (30-day) form, matching the same inputs the live win
        probability is computed from.
    """
    from datetime import date

    from app.services.stats_service import (
        _h2h_from_rows,
        _recent_form_win_rate,
        get_stats_service,
    )

    stats_service = get_stats_service()
    appearances = await stats_service._fetch_resolved_appearances_async()

    h2h = _h2h_from_rows(player_a, player_b, appearances, surface=surface, mod=mod)

    today = date.today()
    a_lower, b_lower = player_a.lower(), player_b.lower()
    form_a = _recent_form_win_rate([a for a in appearances if a["name"].lower() == a_lower], today)
    form_b = _recent_form_win_rate([a for a in appearances if a["name"].lower() == b_lower], today)

    return {
        "h2h": {
            "wins_a": h2h.wins_a,
            "wins_b": h2h.wins_b,
            "total": h2h.total,
            "specific_wins_a": h2h.specific_wins_a,
            "specific_wins_b": h2h.specific_wins_b,
            "specific_total": h2h.specific_total,
        },
        "form_a": form_a,
        "form_b": form_b,
    }


class ConnectionManager:
    """Manages WebSocket connections for live score updates."""

    MAX_CONNECTIONS = 1000

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept.
        """
        if len(self.active_connections) >= self.MAX_CONNECTIONS:
            logger.warning(f"Max connections ({self.MAX_CONNECTIONS}) reached. Rejecting client.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients concurrently.

        Args:
            message: JSON string to broadcast.
        """
        if not self.active_connections:
            return

        results = await asyncio.gather(
            *[conn.send_text(message) for conn in self.active_connections],
            return_exceptions=True,
        )

        # Clean up any connections that raised errors
        failed = [
            conn
            for conn, result in zip(self.active_connections, results)
            if isinstance(result, Exception)
        ]
        for conn in failed:
            self.disconnect(conn)


# Singleton connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_live_scores(
    websocket: WebSocket,
    settings: SettingsDep,
    scraper: ScraperDep,
) -> None:
    """WebSocket endpoint for real-time score updates.

    Clients receive score updates at the configured refresh interval.
    Send any message to keep the connection alive.

    Args:
        websocket: The WebSocket connection.
        settings: Application settings.
        scraper: Scraper service for fetching scores.
    """
    await manager.connect(websocket)

    # Rate limiting for client messages
    # Max messages per minute
    MSG_RATE_LIMIT = 20
    # Time window in seconds
    WINDOW_SECONDS = 60
    
    last_reset_time = time.time()
    msg_count = 0

    # Initialize tasks outside the loop
    update_task = asyncio.create_task(scraper.wait_for_update())
    client_task = asyncio.create_task(websocket.receive_text())

    try:
        # Send initial data immediately if available
        current_data = scraper.get_latest_data()
        if current_data:
            await websocket.send_text(current_data.model_dump_json())

        while True:
            # Wait for either new data OR client message
            done, pending = await asyncio.wait(
                [update_task, client_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Handle Update Task
            if update_task in done:
                # Re-arm update waiter immediately
                update_task = asyncio.create_task(scraper.wait_for_update())
                
                # Send the new data
                if data := scraper.get_latest_data():
                    await websocket.send_text(data.model_dump_json())

            # Handle Client Task (Disconnects/Pings)
            if client_task in done:
                try:
                    # Check result to catch disconnects
                    _ = client_task.result()
                    
                    # Rate Limit Logic
                    current_time = time.time()
                    if current_time - last_reset_time > WINDOW_SECONDS:
                        msg_count = 0
                        last_reset_time = current_time
                    
                    msg_count += 1
                    if msg_count > MSG_RATE_LIMIT:
                        logger.warning("Client exceeded message rate limit. Disconnecting.")
                        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                        break

                    # If successful (just a message/ping), re-arm listener
                    client_task = asyncio.create_task(websocket.receive_text())
                except WebSocketDisconnect:
                    # Client disconnected normally
                    break
                except Exception as e:
                    logger.error(f"Client receive error: {e}")
                    break
                    
    except WebSocketDisconnect:
        # Handled by manager.disconnect in finally
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)
        # Clean up pending tasks
        if not update_task.done():
            update_task.cancel()
        if not client_task.done():
            client_task.cancel()
