"""Live scores API endpoints.

Provides REST and WebSocket endpoints for fetching live tennis match scores.
"""

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.deps import ScraperDep, SettingsDep
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
async def get_live_scores(
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
async def get_today_stats() -> dict:
    """Get today's finished match statistics.

    Returns:
        Today's stats by mod and format.
    """
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return stats_service.get_today_stats()


@router.get(
    "/stats/history",
    summary="Get historical stats",
    description="Get daily stats for the last N days.",
)
async def get_stats_history(
    days: Annotated[int, Query(ge=1, le=90, description="Number of days")] = 7,
) -> list[dict]:
    """Get historical daily statistics.

    Args:
        days: Number of days to retrieve (1-90).

    Returns:
        List of daily stats.
    """
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_history(days)


class ConnectionManager:
    """Manages WebSocket connections for live score updates."""

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept.
        """
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
        """Broadcast a message to all connected clients.

        Args:
            message: JSON string to broadcast.
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
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
