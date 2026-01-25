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

    try:
        while True:
            # Fetch and send scores
            try:
                scores = await scraper.fetch_servers()
                await websocket.send_text(scores.model_dump_json())
            except Exception as e:
                logger.error(f"Error fetching scores: {e}")
                await websocket.send_json({"error": str(e)})

            # Wait for next update or client message
            try:
                # Use wait_for to allow both timeout and incoming messages
                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=float(settings.score_refresh_interval),
                )
            except asyncio.TimeoutError:
                # Normal timeout, continue to next update
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
