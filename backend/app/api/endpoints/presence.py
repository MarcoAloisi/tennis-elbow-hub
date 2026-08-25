"""Presence WebSocket endpoint.

Tracks site-wide online status for guests and registered users. Unlike
get_current_user (deps.py), an invalid/expired/missing token here degrades
to "counted as guest" rather than rejecting the connection — presence is a
headcount, not an access gate.
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import get_user_from_token
from app.core.logging import get_logger
from app.services.presence import presence_manager

logger = get_logger("api.presence")
router = APIRouter(prefix="/presence", tags=["Presence"])


async def _resolve_user_id(websocket: WebSocket) -> str | None:
    """Resolve the connecting client to a Supabase user id, or None for a guest.

    Runs the (synchronous, network-calling) token validation in a thread so
    it never blocks the event loop other connections depend on.
    """
    token = websocket.query_params.get("token")
    if not token:
        return None
    user = await asyncio.to_thread(get_user_from_token, token)
    return user.id if user else None


@router.websocket("/ws")
async def websocket_presence(websocket: WebSocket) -> None:
    """WebSocket endpoint for site-wide presence tracking.

    Clients connect once per tab and keep the connection open for the
    whole session. Broadcasts {"registered_count", "guest_count"} on every
    connect/disconnect. The periodic self-healing safety-net broadcast is
    NOT run from here — it's a single app-wide loop started once from
    main.py's lifespan (see PresenceManager.start_periodic_broadcast) so
    it stays O(1) loops regardless of connection count, not one per client.
    """
    user_id = await _resolve_user_id(websocket)

    accepted = await presence_manager.connect(websocket, user_id)
    if not accepted:
        return

    await presence_manager.broadcast_counts()

    try:
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Presence client receive error: {e}")
                break
    finally:
        presence_manager.disconnect(websocket, user_id)
        await presence_manager.broadcast_counts()
