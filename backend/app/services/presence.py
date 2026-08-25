"""Presence tracking for site-wide online status.

Tracks connected WebSocket clients in-memory, split into registered users
(deduped by Supabase user id, so multiple tabs count once) and guests (no
identity, each tab counted raw). Mirrors the ConnectionManager pattern in
live_scores.py.
"""

import asyncio
import json

from fastapi import WebSocket, status

from app.core.logging import get_logger

logger = get_logger("services.presence")


class PresenceManager:
    """Tracks which guests and registered users currently have a connection open."""

    MAX_CONNECTIONS = 1000

    def __init__(self) -> None:
        self.registered: dict[str, set[WebSocket]] = {}
        self.guests: set[WebSocket] = set()
        self._broadcast_task: asyncio.Task | None = None

    @property
    def total_connections(self) -> int:
        return len(self.guests) + sum(len(conns) for conns in self.registered.values())

    @property
    def counts(self) -> dict[str, int]:
        return {
            "registered_count": len(self.registered),
            "guest_count": len(self.guests),
        }

    def is_online(self, user_id: str) -> bool:
        return user_id in self.registered

    async def connect(self, websocket: WebSocket, user_id: str | None) -> bool:
        """Accept and track a connection. Returns False if rejected (at capacity)."""
        if self.total_connections >= self.MAX_CONNECTIONS:
            logger.warning(f"Max presence connections ({self.MAX_CONNECTIONS}) reached. Rejecting client.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

        await websocket.accept()
        if user_id:
            self.registered.setdefault(user_id, set()).add(websocket)
        else:
            self.guests.add(websocket)
        logger.info(f"Presence connect (user_id={user_id}). Total: {self.total_connections}")
        return True

    def disconnect(self, websocket: WebSocket, user_id: str | None) -> None:
        """Remove a tracked connection."""
        if user_id and user_id in self.registered:
            self.registered[user_id].discard(websocket)
            if not self.registered[user_id]:
                del self.registered[user_id]
        else:
            self.guests.discard(websocket)
        logger.info(f"Presence disconnect (user_id={user_id}). Total: {self.total_connections}")

    async def broadcast_counts(self) -> None:
        """Broadcast current counts to every connected client."""
        message = json.dumps(self.counts)
        all_sockets = list(self.guests) + [
            ws for conns in self.registered.values() for ws in conns
        ]
        if not all_sockets:
            return

        results = await asyncio.gather(
            *[ws.send_text(message) for ws in all_sockets],
            return_exceptions=True,
        )

        # A failed send means the socket is dead — clean it up wherever it's
        # tracked. We don't know here if it was a guest or registered
        # connection, so try both; the wrong one is always a no-op discard.
        for ws, result in zip(all_sockets, results):
            if isinstance(result, Exception):
                self.guests.discard(ws)
                for uid, conns in list(self.registered.items()):
                    conns.discard(ws)
                    if not conns:
                        del self.registered[uid]

    async def start_periodic_broadcast(self, interval: int = 30) -> None:
        """Start the app-wide periodic self-healing broadcast loop.

        This is a single loop for the whole app (mirrors ScraperService's
        start_polling in scraper.py), not one per connection — a
        per-connection timer would broadcast to all N clients from each of
        N clients on every tick, which is O(N^2) message volume instead of
        O(N). Meant to be called once from main.py's lifespan.

        Args:
            interval: Seconds between broadcasts.
        """
        if self._broadcast_task and not self._broadcast_task.done():
            logger.warning("Periodic presence broadcast already started")
            return

        logger.info(f"Starting periodic presence broadcast (interval={interval}s)")
        self._broadcast_task = asyncio.create_task(self._broadcast_loop(interval))

    async def stop_periodic_broadcast(self) -> None:
        """Stop the periodic broadcast loop."""
        if self._broadcast_task:
            logger.info("Stopping periodic presence broadcast")
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            self._broadcast_task = None

    async def _broadcast_loop(self, interval: int) -> None:
        """Background loop broadcasting counts on a fixed interval.

        Self-healing safety net: connect/disconnect already broadcast
        immediately, this catches anything a missed send left stale.

        Args:
            interval: Sleep interval between broadcasts.
        """
        while True:
            await asyncio.sleep(interval)
            try:
                await self.broadcast_counts()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in presence broadcast loop: {e}")


# Singleton presence manager
presence_manager = PresenceManager()
