# Presence Tracking + Admin Users View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track site-wide online presence (guest vs. registered) in real time, expose it to admins as a per-user online flag, and show a live "N members · M guests online" count in the site footer.

**Architecture:** A new in-memory `PresenceManager` singleton (mirrors the existing `ConnectionManager` in `live_scores.py`) tracks connected WebSocket clients, deduped by Supabase user id for registered users. A new `/api/presence/ws` endpoint accepts every browser tab's connection, resolving it to guest or registered by an optional `?token=` query param that fails open to guest on any auth problem. Admins query `/admin/users` for the full `user_profiles` list annotated with a live `online` flag from the same singleton. The frontend opens one presence WebSocket per tab at app root and reconnects it whenever login state changes.

**Tech Stack:** FastAPI WebSocket (backend), Vue 3 + Pinia (frontend), pytest + pytest-asyncio (backend tests, `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed).

**Spec:** `docs/superpowers/specs/2026-08-25-presence-admin-users-design.md`

## Global Constraints

- Backend is a single uvicorn process on the IONOS VPS (`infra/te4-backend.service`, no `--workers` flag) — in-memory singleton state (`presence_manager`) is safe, no cross-instance fragmentation to guard against.
- The nginx WebSocket proxy fix (`infra/nginx.conf`) and this plan's spec doc are **already committed** (commit `1a1bf82`) — not a task in this plan.
- Every public REST route gets `@limiter.limit(...)` + a `request: Request` param (CLAUDE.md convention, followed throughout `admin.py`). WebSocket routes in this codebase (`live_scores.py`'s `/ws`) do not carry `@limiter.limit` — presence follows the same precedent.
- Presence token validation must **fail open to guest**, never reject the connection — this is deliberately the opposite of `get_current_user`'s fail-closed behavior (spec, "Backend: presence WebSocket endpoint").
- No new DB model, no Alembic migration — presence state is in-memory only.
- This repo has **no test-DB isolation** — every existing backend test either avoids the DB entirely or only exercises the pre-auth-check 401/422 path. Do not write a test that reaches `db.execute(...)` for a real query; `.env`'s `DATABASE_URL` points at the live production Supabase instance.
- Frontend has no test framework wired up (`npm run test` script exists in `package.json` but zero `*.test.ts`/`*.spec.ts` files exist in the repo). Frontend tasks use `npm run type-check` as the automated gate and end in manual browser verification (Task 8) — do not introduce a new test framework as part of this plan.

---

## Task 1: PresenceManager service

**Files:**
- Create: `backend/app/services/presence.py`
- Test: `backend/tests/test_presence.py`

**Interfaces:**
- Produces: `PresenceManager` class with `async connect(websocket: WebSocket, user_id: str | None) -> bool`, `disconnect(websocket: WebSocket, user_id: str | None) -> None`, `async broadcast_counts() -> None`, `is_online(user_id: str) -> bool`, `counts: dict[str, int]` (`{"registered_count": int, "guest_count": int}`), `total_connections: int`, `async start_periodic_broadcast(interval: int = 30) -> None`, `async stop_periodic_broadcast() -> None`. Module-level singleton `presence_manager = PresenceManager()`. Task 2 imports and drives `connect`/`disconnect`/`broadcast_counts`; Task 2 also wires `start_periodic_broadcast`/`stop_periodic_broadcast` into `main.py`'s lifespan.

**Design note:** the periodic safety-net broadcast is a single app-wide loop (mirroring `ScraperService.start_polling`/`stop_polling` in `scraper.py:54-76`, started once from `main.py`'s lifespan), **not** a per-connection timer. A per-connection timer would mean N concurrent clients each independently broadcasting to all N clients every interval — O(N²) message volume instead of O(N). One global loop keeps it O(N) per tick regardless of how many clients are connected.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for PresenceManager — in-memory site-wide online tracking."""

from app.services.presence import PresenceManager


class FakeWebSocket:
    """Minimal stand-in for FastAPI's WebSocket in unit tests."""

    def __init__(self) -> None:
        self.accepted = False
        self.closed_code: int | None = None
        self.sent: list[str] = []
        self.fail_send = False

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int | None = None) -> None:
        self.closed_code = code

    async def send_text(self, message: str) -> None:
        if self.fail_send:
            raise RuntimeError("connection closed")
        self.sent.append(message)


async def test_guest_connect_is_tracked_and_counted():
    manager = PresenceManager()
    ws = FakeWebSocket()

    accepted = await manager.connect(ws, None)

    assert accepted is True
    assert ws.accepted is True
    assert manager.counts == {"registered_count": 0, "guest_count": 1}


async def test_registered_connect_dedupes_multiple_tabs():
    manager = PresenceManager()
    tab1, tab2 = FakeWebSocket(), FakeWebSocket()

    await manager.connect(tab1, "user-1")
    await manager.connect(tab2, "user-1")

    assert manager.counts == {"registered_count": 1, "guest_count": 0}
    assert manager.is_online("user-1") is True


async def test_disconnect_removes_guest():
    manager = PresenceManager()
    ws = FakeWebSocket()
    await manager.connect(ws, None)

    manager.disconnect(ws, None)

    assert manager.counts == {"registered_count": 0, "guest_count": 0}


async def test_disconnect_last_tab_marks_user_offline():
    manager = PresenceManager()
    ws = FakeWebSocket()
    await manager.connect(ws, "user-1")

    manager.disconnect(ws, "user-1")

    assert manager.is_online("user-1") is False
    assert manager.counts == {"registered_count": 0, "guest_count": 0}


async def test_disconnect_one_of_two_tabs_keeps_user_online():
    manager = PresenceManager()
    tab1, tab2 = FakeWebSocket(), FakeWebSocket()
    await manager.connect(tab1, "user-1")
    await manager.connect(tab2, "user-1")

    manager.disconnect(tab1, "user-1")

    assert manager.is_online("user-1") is True
    assert manager.counts == {"registered_count": 1, "guest_count": 0}


async def test_connect_rejects_when_at_capacity():
    manager = PresenceManager()
    manager.MAX_CONNECTIONS = 1
    first = FakeWebSocket()
    await manager.connect(first, None)

    second = FakeWebSocket()
    accepted = await manager.connect(second, None)

    assert accepted is False
    assert second.accepted is False
    assert second.closed_code == 1008


async def test_broadcast_counts_sends_to_all_and_cleans_up_failed_sockets():
    manager = PresenceManager()
    good = FakeWebSocket()
    bad = FakeWebSocket()
    bad.fail_send = True
    await manager.connect(good, None)
    await manager.connect(bad, "user-1")

    await manager.broadcast_counts()

    assert good.sent == ['{"registered_count": 1, "guest_count": 1}']
    assert manager.is_online("user-1") is False
    assert manager.counts == {"registered_count": 0, "guest_count": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_presence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.presence'`

- [ ] **Step 3: Write the implementation**

```python
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
```

Note: `start_periodic_broadcast`/`stop_periodic_broadcast` aren't unit tested here, matching this codebase's existing convention — `ScraperService.start_polling`/`stop_polling` in `scraper.py` (the pattern this mirrors) has no dedicated tests either; that class of task-lifecycle bookkeeping is covered by manual/integration verification (Task 8) instead.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_presence.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/presence.py backend/tests/test_presence.py
git commit -m "feat: add PresenceManager for site-wide online tracking"
```

---

## Task 2: Presence WebSocket endpoint

**Files:**
- Modify: `backend/app/api/deps.py:55-91` (extract `get_user_from_token`, refactor `get_current_user` to use it)
- Create: `backend/app/api/endpoints/presence.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/main.py` (start/stop the periodic broadcast loop in the app lifespan)
- Modify: `backend/tests/test_presence.py` (append WebSocket-level tests)

**Interfaces:**
- Consumes: `presence_manager` (Task 1) — `connect`, `disconnect`, `broadcast_counts`, `counts`, `is_online`, `start_periodic_broadcast`, `stop_periodic_broadcast`.
- Produces: `get_user_from_token(token: str) -> Any | None` in `deps.py`, reused by any future caller wanting fail-open auth. `router` (presence router, prefix `/presence`) mounted under `/api`, so the live route is `/api/presence/ws`.

- [ ] **Step 1: Refactor `deps.py` to extract `get_user_from_token`**

Replace `backend/app/api/deps.py:55-91` (the current `get_current_user` function) with:

```python
def get_user_from_token(token: str) -> Any | None:
    """Validate a Supabase JWT and return the user, or None if it's invalid/expired.

    Unlike get_current_user, this never raises. Callers that should fail
    open on a bad token (e.g. presence tracking, which is a headcount, not
    an access gate) call this directly instead of the get_current_user
    dependency.
    """
    try:
        supabase = get_supabase()
        user_response = supabase.auth.get_user(token)
        return user_response.user if user_response and user_response.user else None
    except Exception:
        logger.exception("Token validation failed")
        return None


def get_current_user(authorization: Annotated[str, Header()]) -> Any:
    """Verify the JWT token and return the Supabase user.

    Raises:
        HTTPException 401: If the token is missing, invalid, or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    user = get_user_from_token(parts[1])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user
```

- [ ] **Step 2: Verify the refactor didn't break existing auth tests**

Run: `cd backend && pytest tests/test_profile_api.py -v`
Expected: PASS (same 401/422 assertions as before — behavior is unchanged, only the internal structure moved)

- [ ] **Step 3: Write the failing WebSocket tests**

Append to `backend/tests/test_presence.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.presence import presence_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_presence_manager():
    presence_manager.registered.clear()
    presence_manager.guests.clear()
    yield
    presence_manager.registered.clear()
    presence_manager.guests.clear()


def test_presence_ws_guest_connect_receives_counts():
    with client.websocket_connect("/api/presence/ws") as ws:
        data = ws.receive_json()
        assert data == {"registered_count": 0, "guest_count": 1}


def test_presence_ws_invalid_token_counts_as_guest(monkeypatch):
    monkeypatch.setattr("app.api.endpoints.presence.get_user_from_token", lambda token: None)
    with client.websocket_connect("/api/presence/ws?token=bad-token") as ws:
        data = ws.receive_json()
        assert data == {"registered_count": 0, "guest_count": 1}


def test_presence_ws_valid_token_counts_as_registered(monkeypatch):
    class FakeUser:
        id = "user-123"

    monkeypatch.setattr("app.api.endpoints.presence.get_user_from_token", lambda token: FakeUser())
    with client.websocket_connect("/api/presence/ws?token=good-token") as ws:
        data = ws.receive_json()
        assert data == {"registered_count": 1, "guest_count": 0}
        assert presence_manager.is_online("user-123") is True


def test_presence_ws_disconnect_updates_counts():
    with client.websocket_connect("/api/presence/ws") as ws:
        ws.receive_json()  # initial broadcast, ignored

    # First connection is fully closed by now. A second connection's
    # initial broadcast should reflect that the first one is gone.
    with client.websocket_connect("/api/presence/ws") as ws2:
        data = ws2.receive_json()
        assert data == {"registered_count": 0, "guest_count": 1}
```

Note: the `reset_presence_manager` fixture is `autouse=True` and file-scoped — it's harmless for Task 1's tests above (they construct their own local `PresenceManager()` instances and never touch the singleton).

- [ ] **Step 4: Run tests to verify the new ones fail**

Run: `cd backend && pytest tests/test_presence.py -v -k presence_ws`
Expected: FAIL (no route at `/api/presence/ws` yet — connection rejected)

- [ ] **Step 5: Write the presence WebSocket endpoint**

Create `backend/app/api/endpoints/presence.py`:

```python
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
```

- [ ] **Step 6: Register the router**

Modify `backend/app/api/router.py`:

```python
from app.api.endpoints import (
    admin,
    contact,
    guides,
    live_scores,
    match_analysis,
    outfits,
    predictions,
    presence,
    profile,
    real_tennis,
    tour_logs,
)

# Create the main API router
api_router = APIRouter(prefix="/api")

# Include sub-routers
api_router.include_router(live_scores.router)
api_router.include_router(match_analysis.router)
api_router.include_router(tour_logs.router)
api_router.include_router(outfits.router)
api_router.include_router(guides.router)
api_router.include_router(contact.router)
api_router.include_router(admin.router)
api_router.include_router(predictions.router)
api_router.include_router(profile.router)
api_router.include_router(real_tennis.router)
api_router.include_router(presence.router)
```

(Only the import list gains `presence,` and one `include_router` line is added — everything else in the file is unchanged.)

- [ ] **Step 7: Start and stop the periodic broadcast loop from the app lifespan**

Modify `backend/app/main.py`. Add the import alongside the existing scraper import (line 24):

```python
from app.services.scraper import get_scraper_service
from app.services.presence import presence_manager
```

Then in the `lifespan` function, add the startup call right after `await scraper.start_polling(interval=interval)` (currently line 61, right before `yield`):

```python
    await scraper.start_polling(interval=interval)

    await presence_manager.start_periodic_broadcast()

    yield
```

And add the shutdown call right after `logger.info("Shutting down...")` (currently line 66), before the scraper is stopped:

```python
    # Shutdown
    logger.info("Shutting down...")

    await presence_manager.stop_periodic_broadcast()

    # Stop background polling
    scraper = get_scraper_service()
    await scraper.stop_polling()
```

- [ ] **Step 8: Run all presence tests to verify they pass**

Run: `cd backend && pytest tests/test_presence.py -v`
Expected: PASS (11 tests total: 7 from Task 1 + 4 from this task). These tests don't exercise `main.py`'s lifespan (this repo's tests use a bare `TestClient(app)`, not the `with TestClient(app) as client:` form, so startup/shutdown handlers never run) — that's consistent with every other test in this suite and is why `init_db()` doesn't fire during test runs either. The lifespan wiring itself is covered by Task 8's manual verification.

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/deps.py backend/app/api/endpoints/presence.py backend/app/api/router.py backend/app/main.py backend/tests/test_presence.py
git commit -m "feat: add presence WebSocket endpoint with fail-open guest auth"
```

---

## Task 3: Admin users endpoint

**Files:**
- Modify: `backend/app/api/endpoints/admin.py`
- Test: `backend/tests/test_admin_users.py`

**Interfaces:**
- Consumes: `presence_manager.is_online(user_id: str) -> bool` (Task 1).
- Produces: `GET /api/admin/users` → `list[dict]`, each with keys `user_id, display_name, in_game_name, player_name, approved, created_at, online`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_admin_users.py`:

```python
"""Tests for the /admin/users endpoint.

Only the unauthenticated path is tested here — this repo has no test-DB
isolation (see plan's Global Constraints), and the endpoint's happy path
queries the live user_profiles table, so it isn't safe to exercise with a
bypassed auth dependency in an automated test. The online-flag computation
itself (presence_manager.is_online) is covered by test_presence.py.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_users_unauthenticated():
    response = client.get("/api/admin/users")
    assert response.status_code in (401, 422)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_admin_users.py -v`
Expected: FAIL with 404 (route doesn't exist yet) instead of 401/422

- [ ] **Step 3: Add the endpoint**

Add to `backend/app/api/endpoints/admin.py`, after the `# ─── Signup Approvals ───` section (after `approve_signup`, currently the last function in the file):

```python
# ─── Registered Users ───────────────────────────────────────


@router.get(
    "/users",
    summary="List all registered users",
    description="List every registered user with their live online status. Admin only.",
)
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    _admin: Any = Depends(require_admin),
    db=Depends(get_db),
) -> list[dict]:
    """List all registered users with a live online/offline flag."""
    from app.services.presence import presence_manager

    result = await db.execute(select(UserProfile).order_by(UserProfile.created_at.desc()))
    profiles = result.scalars().all()
    return [
        {
            "user_id": p.id,
            "display_name": p.display_name,
            "in_game_name": p.in_game_name,
            "player_name": p.player_name,
            "approved": p.approved,
            "created_at": p.created_at,
            "online": presence_manager.is_online(p.id),
        }
        for p in profiles
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_admin_users.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/admin.py backend/tests/test_admin_users.py
git commit -m "feat: add admin endpoint listing registered users with online status"
```

---

## Task 4: Reactive URL + configurable reconnect in `useWebSocket`

**Files:**
- Modify: `frontend/src/composables/useWebSocket.ts`

**Interfaces:**
- Produces: `useWebSocket(url: string | (() => string), options?: { maxReconnectAttempts?: number })` — same return shape as before (`data, isConnected, error, reconnectAttempts, connect, disconnect, send`). Existing callers passing a plain string with no second argument are unaffected. Task 5 consumes the function-url and `maxReconnectAttempts` forms.

- [ ] **Step 1: Modify the composable**

Replace the top of `frontend/src/composables/useWebSocket.ts` (lines 1-31) with:

```typescript
/**
 * WebSocket composable for real-time data
 */
import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket(url, options: { maxReconnectAttempts?: number } = {}) {
    const data = ref(null)
    const isConnected = ref(false)
    const error = ref(null)
    const reconnectAttempts = ref(0)

    let socket = null
    let reconnectTimeout = null
    const MAX_RECONNECT_ATTEMPTS = options.maxReconnectAttempts ?? 5
    const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000]

    /**
     * Connect to WebSocket server
     */
    function connect() {
        if (socket?.readyState === WebSocket.OPEN) {
            return
        }

        try {
            // Resolve the URL fresh on every (re)connect — lets callers pass
            // a function so a changed token (or anything else) is picked up
            // without the composable needing to know why the URL changed.
            const rawUrl = typeof url === 'function' ? url() : url

            // Build WebSocket URL
            const wsUrl = rawUrl.startsWith('ws')
                ? rawUrl
                : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${rawUrl}`

            socket = new WebSocket(wsUrl)
```

Everything below this point in the file (from `socket.onopen = () => {` through the end) stays exactly as it is — only the function signature and the URL-resolution line inside `connect()` change.

- [ ] **Step 2: Verify existing usage still type-checks**

Run: `cd frontend && npm run type-check`
Expected: PASS, no new errors (in particular, `LiveScoresView.vue:18`'s `useWebSocket(wsUrl('/api/scores/ws'))` call — a plain string, no options — must still compile)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useWebSocket.ts
git commit -m "feat: support reactive URL and configurable reconnect limit in useWebSocket"
```

---

## Task 5: Frontend presence store

**Files:**
- Create: `frontend/src/stores/presence.ts`

**Interfaces:**
- Consumes: `useWebSocket` (Task 4), `useAuthStore` (`stores/auth.ts` — `session` ref with `.access_token`), `wsUrl` (`config/api.ts`).
- Produces: `usePresenceStore()` Pinia store exposing reactive `registeredCount: Ref<number>`, `guestCount: Ref<number>`. Task 6 consumes both.

- [ ] **Step 1: Write the store**

Create `frontend/src/stores/presence.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAuthStore } from './auth'
import { wsUrl } from '@/config/api'

export const usePresenceStore = defineStore('presence', () => {
    const registeredCount = ref(0)
    const guestCount = ref(0)
    const authStore = useAuthStore()

    function buildUrl(): string {
        const token = authStore.session?.access_token
        return wsUrl(token ? `/api/presence/ws?token=${encodeURIComponent(token)}` : '/api/presence/ws')
    }

    // maxReconnectAttempts: Infinity — this connection represents the
    // visitor's whole session, unlike a page-scoped widget where giving up
    // after a few tries and telling the user to refresh is acceptable.
    const { data, connect, disconnect } = useWebSocket(buildUrl, { maxReconnectAttempts: Infinity })

    watch(data, (message: any) => {
        if (!message) return
        if (typeof message.registered_count === 'number') registeredCount.value = message.registered_count
        if (typeof message.guest_count === 'number') guestCount.value = message.guest_count
    })

    // A tab that logs in or out mid-session must be re-classified without a
    // page reload: drop the old connection and reconnect with the new token
    // (or none). The very first connect — which happens before authStore's
    // initAuth() has necessarily resolved — will naturally be as a guest
    // and gets corrected here as soon as the real session loads.
    watch(
        () => authStore.session?.access_token,
        () => {
            disconnect()
            connect()
        }
    )

    return { registeredCount, guestCount }
})
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npm run type-check`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/presence.ts
git commit -m "feat: add presence Pinia store"
```

---

## Task 6: Wire presence into App.vue and the footer

**Files:**
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `usePresenceStore` (Task 5).

- [ ] **Step 1: Import and instantiate the store**

In `frontend/src/App.vue`, modify the import block around line 18 — add the presence store import right after the auth store import:

```typescript
import { useAuthStore } from './stores/auth'
import { usePresenceStore } from './stores/presence'
```

Then, right after `const authStore = useAuthStore()` (line 29), add:

```typescript
const presenceStore = usePresenceStore()
```

This **must** be a top-level call in `<script setup>`, not inside `onMounted` — `usePresenceStore()` is what runs the store's setup function (including its internal `useWebSocket` call, which registers its own `onMounted`/`onUnmounted`), and that only binds correctly to this component's lifecycle if it executes during App.vue's own `setup()`. This matches the existing `useModalAccessibility(...)` call at line 48, which is called the same way for the same reason.

- [ ] **Step 2: Show the counts in the footer**

Modify the footer template at `frontend/src/App.vue:220-221`:

```html
    <!-- Footer -->
    <footer class="app-footer">
      <p>Tennis Elbow Hub &copy; 2026 — Tennis Elbow 4 Live Scores & Analysis</p>
      <p class="footer-presence">{{ presenceStore.registeredCount }} members · {{ presenceStore.guestCount }} guests online</p>
      <div class="footer-links">
```

- [ ] **Step 3: Style the new line**

Add to the `<style scoped>` block, right after `.app-footer { ... }` (around line 562):

```css
.footer-presence {
  margin-top: var(--space-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
```

- [ ] **Step 4: Type-check**

Run: `cd frontend && npm run type-check`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: show live presence counts in the footer"
```

---

## Task 7: Admin Users page

**Files:**
- Create: `frontend/src/views/AdminUsersView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `GET /api/admin/users` (Task 3).

- [ ] **Step 1: Create the view**

Create `frontend/src/views/AdminUsersView.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase } from '@/config/supabase'
import { apiUrl } from '@/config/api'
import { RefreshCw, User } from 'lucide-vue-next'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'

interface AdminUser {
  user_id: string
  display_name: string | null
  in_game_name: string | null
  player_name: string | null
  approved: boolean
  created_at: string
  online: boolean
}

const users = ref<AdminUser[]>([])
const isLoading = ref(false)
const error = ref('')

async function getAuthHeaders() {
  const { data } = await supabase.auth.getSession()
  return { Authorization: `Bearer ${data.session?.access_token}` }
}

async function fetchUsers() {
  isLoading.value = true
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const res = await fetch(apiUrl('/api/admin/users'), { headers })
    if (!res.ok) throw new Error(`Failed to load users (${res.status})`)
    users.value = await res.json()
  } catch (e: any) {
    error.value = e.message || 'Failed to load users.'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="admin-users">
    <div class="admin-users-header">
      <h1><User :size="24" /> Registered Users</h1>
      <button class="btn-refresh" @click="fetchUsers" :disabled="isLoading">
        <RefreshCw :size="16" :class="{ spinning: isLoading }" /> Refresh
      </button>
    </div>

    <ErrorAlert v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading && !users.length" />

    <table v-if="users.length" class="users-table">
      <thead>
        <tr>
          <th>Status</th>
          <th>Display Name</th>
          <th>In-Game Name</th>
          <th>Approved</th>
          <th>Joined</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.user_id">
          <td>
            <span
              class="status-dot"
              :class="u.online ? 'online' : 'offline'"
              :title="u.online ? 'Online' : 'Offline'"
            ></span>
          </td>
          <td>{{ u.display_name || '—' }}</td>
          <td>{{ u.in_game_name || '—' }}</td>
          <td>{{ u.approved ? 'Yes' : 'No' }}</td>
          <td>{{ new Date(u.created_at).toLocaleDateString() }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!isLoading">No registered users yet.</p>
  </div>
</template>

<style scoped>
.admin-users {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--space-6);
}

.admin-users-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.admin-users-header h1 {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-xl);
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th,
.users-table td {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-dot.online {
  background: #22c55e;
}

.status-dot.offline {
  background: var(--color-text-muted);
}
</style>
```

- [ ] **Step 2: Register the route**

In `frontend/src/router/index.ts`, add the lazy import next to the other admin views (around line 16):

```typescript
const AdminPlayersView = () => import('../views/AdminPlayersView.vue')
const AdminPanelView = () => import('../views/AdminPanelView.vue')
const AdminUsersView = () => import('../views/AdminUsersView.vue')
```

Then add the route right after the `/admin/panel` block (around line 231):

```typescript
    {
        path: '/admin/panel',
        name: 'AdminPanel',
        component: AdminPanelView,
        meta: {
            title: 'Admin Panel',
            description: 'Admin panel for managing player link verifications.',
            requiresAdmin: true
        }
    },
    {
        path: '/admin/users',
        name: 'AdminUsers',
        component: AdminUsersView,
        meta: {
            title: 'Registered Users',
            description: 'Admin-only list of registered users with live online status.',
            requiresAdmin: true
        }
    }
]
```

(Note the trailing `]` — this is the end of the routes array, so the comma moves to after the `AdminPanel` block and the new block closes the array as shown.)

- [ ] **Step 3: Add the nav link**

In `frontend/src/App.vue`, add a link in the admin dropdown right after the Admin Panel link (`App.vue:152-154`):

```html
                    <RouterLink to="/admin/panel" class="dropdown-item dropdown-item--admin">
                      <Shield :size="15" /> Admin Panel
                    </RouterLink>
                    <RouterLink to="/admin/users" class="dropdown-item dropdown-item--admin">
                      <User :size="15" /> Registered Users
                    </RouterLink>
```

(`User` is already imported at `App.vue:25` for the "My Profile" link — no new import needed.)

- [ ] **Step 4: Type-check**

Run: `cd frontend && npm run type-check`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/AdminUsersView.vue frontend/src/router/index.ts frontend/src/App.vue
git commit -m "feat: add admin registered-users page with online status"
```

---

## Task 8: Manual end-to-end verification

No code changes — this closes out the spec's testing requirements that can't be automated in this repo (per Global Constraints: no frontend test framework, no test-DB isolation).

- [ ] **Step 1: Start both services**

Run: `./start-dev.ps1` from the repo root (or `uvicorn app.main:app --reload` in `backend/` and `npm run dev` in `frontend/` separately).

- [ ] **Step 2: Verify live presence counts**

Open the site in two browser tabs (or one normal + one private/incognito window). In the footer of both, confirm "N members · M guests online" appears and increments as each tab loads. Close one tab; confirm the count in the remaining tab drops within a few seconds (either from the disconnect broadcast or the 30s periodic broadcast — wait up to 30s to be sure the periodic path works too, not just the connect/disconnect path).

- [ ] **Step 3: Verify guest → registered transition**

With a tab open and counted as a guest, log in without refreshing the page. Confirm the footer's guest count drops by one and the registered/members count rises by one — this proves the `watch` on `authStore.session?.access_token` in `stores/presence.ts` is reconnecting correctly.

- [ ] **Step 4: Verify the admin Users page**

Log in as an admin (an account with `app_metadata.role == "admin"` in Supabase). Navigate to Account menu → Registered Users (`/admin/users`). Confirm your own account shows as online (green dot) while any other listed account you're not simultaneously logged into shows offline.

- [ ] **Step 5: Verify `LiveScoresView` still works**

Navigate to the Live Scores page. Confirm it still connects and updates — this is the regression check for Task 4's change to `useWebSocket.ts`, which is shared with `LiveScoresView.vue:18`.

- [ ] **Step 6: Post-deploy nginx regression check (IONOS VPS only, not local dev)**

After deploying this branch to the VPS via `infra/deploy.sh` and reloading nginx (`sudo nginx -t && sudo systemctl reload nginx` — `deploy.sh` does not do this automatically, it only restarts the backend systemd service), verify both WebSocket routes upgrade correctly through the already-fixed `infra/nginx.conf`: `wss://api.tenniselbowhub.live/api/scores/ws` (pre-existing live-scores route, regression check on the nginx fix from commit `1a1bf82`) and `wss://api.tenniselbowhub.live/api/presence/ws` (new).
