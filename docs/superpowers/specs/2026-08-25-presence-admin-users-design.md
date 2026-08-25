# Presence tracking + admin users view — design

Date: 2026-08-25
Branch: `ionos-migration`

## Problem

Admins have no view of who is registered on the site, and no visibility into who's currently active. There's also no public-facing "how many people are here right now" stat. The site is unauthenticated-by-default (no login wall), so any solution needs a notion of "guest" (anonymous visitor) vs "registered" (has an account) — that distinction doesn't exist anywhere in the codebase today.

## Scope

- Guest = no Supabase account. Registered = has one. No further sub-categories.
- Real-time online/offline presence for both guests and registered users.
- Admin page: list of registered users (from `user_profiles`) with an online/offline indicator.
- Public footer widget: live count of registered-online vs guest-online, split.
- A pre-existing nginx WebSocket proxy bug on the IONOS VPS that would otherwise block this feature (and likely already blocks live-scores WS in prod).

Out of scope: historical presence/analytics, per-guest identity or tracking beyond a raw connection count, horizontal scaling of the backend (single VPS process today — see Deployment Context).

## Deployment context (verified, not assumed)

Real production hosting is an IONOS VPS for the backend and Cloudflare Pages for the frontend — **not** Render. `render.yaml` and `DEPLOYMENT.md` at the repo root are stale leftovers from an earlier hosting setup and were not used to inform this design.

Verified from `infra/`:
- `infra/te4-backend.service` — systemd unit running `uvicorn app.main:app` with no `--workers` flag → **single process** on the VPS. In-memory server-side state (connection managers, presence maps) is safe from cross-instance fragmentation as of this design. If the deployment ever moves to multiple workers/instances, in-memory presence would need to move to shared state (e.g. Redis) — not needed now, not building it now.
- `infra/nginx.conf` had a bug: the `location /ws/` block carried the WebSocket `Upgrade`/`Connection` headers, but the only real WS route in the frontend (`wsUrl('/api/scores/ws')`, `LiveScoresView.vue:18`) falls under `location /api/`, which had no upgrade headers. `/ws/` was dead code — nothing in the frontend calls it. **Already fixed** in this branch: replaced with a regex location `~ ^/api/.*/ws$` (matched before the generic `/api/` block) carrying the upgrade headers, so both `/api/scores/ws` and the new `/api/presence/ws` proxy correctly. This needs `sudo nginx -t && sudo systemctl reload nginx` on the VPS after deploy — `infra/deploy.sh` does not currently reload nginx, only the backend systemd service, so call this out at deploy time.
- `frontend/public/_headers` (Cloudflare Pages CSP) already whitelists `wss://api.tenniselbowhub.live` and `https://api.tenniselbowhub.live` in `connect-src`. No CSP change needed — the presence WS is same-origin API host, just a different path.
- Confirmed no branch/remote drift: `main` and `ionos-migration` are the only two branches, local `ionos-migration` matches `origin/ionos-migration` exactly, single GitHub remote.

## Architecture

### Backend: presence service (new)

`app/services/presence.py` — a singleton `PresenceManager`, in-process, following the same shape as `ConnectionManager` in `live_scores.py`:

```python
class PresenceManager:
    registered: dict[str, set[WebSocket]]   # user_id -> tabs (dedupes multi-tab per account)
    guests: set[WebSocket]                   # no identity; each tab counted raw
```

Methods: `connect(websocket, user_id: str | None)`, `disconnect(websocket, user_id: str | None)`, and computed `counts` (`{registered: len(registered), guests: len(guests)}`) and `is_online(user_id) -> bool`.

### Backend: presence WebSocket endpoint (new)

`app/api/endpoints/presence.py`, mounted at `/api/presence`, route `/ws` → full path `/api/presence/ws`.

- Client connects with optional `?token=<supabase_access_token>` query param — a browser `WebSocket` can't send an `Authorization` header, so the token travels in the URL, same constraint every WS-with-auth implementation hits.
- Token validation reuses the same `supabase.auth.get_user(token)` call `get_current_user` uses in `deps.py`. **Fails open, not closed**: missing or invalid/expired token → treated as guest, connection still accepted. This is the opposite of `require_admin`/`get_current_user`'s fail-closed behavior, and deliberately so — presence is a headcount, not an access gate, so a stale token should degrade to "counted as guest," never boot the visitor.
- Connection lifecycle mirrors `live_scores.py`'s proven pattern exactly: `await websocket.receive_text()` in a loop inside `try/finally`, so any disconnect — clean close, dropped WiFi, laptop sleep, anything — raises and the `finally` block calls `manager.disconnect()`. This is what correctly reaps ungraceful disconnects; no custom ping/pong needed on top of it.
- On every connect and disconnect, broadcast the current `{registered_count, guest_count}` to all connected sockets — this is also how clients get their live count, no separate polling endpoint.
- **Reliability addition**: also broadcast counts on a 30s periodic timer (`asyncio` background task), independent of connect/disconnect events. This is defense-in-depth self-healing — if one broadcast silently fails to reach a socket that's about to die, the next periodic tick corrects it within 30s rather than leaving a stale count indefinitely.
- Same `MAX_CONNECTIONS` style cap as `live_scores.py` (mirror the 1000 limit) as a defensive ceiling, not because hundreds of users is expected to approach it — a single asyncio process handles that easily, `live_scores.py` already proves this pattern at this scale in this codebase.

### Backend: admin users endpoint (new)

`GET /admin/users` in `admin.py`, next to the existing `/admin/pending-signups` pattern — unpaged (matches the documented `/admin/players` precedent in CLAUDE.md), admin-only via `require_admin`. Returns every `UserProfile` row (`display_name`, `in_game_name`, `player_name`, `approved`, `created_at`) plus a computed `online: bool` from `PresenceManager.registered` (`user_id in presence_manager.registered`).

### Frontend

- `frontend/src/stores/presence.ts` — new Pinia store. Opens the presence WS once at app root (`App.vue`), holding it open for the whole session (this *is* the visitor's presence signal, not just a data feed). Exposes reactive `registeredCount` / `guestCount`, updated on every broadcast message.
- Reuses `useWebSocket.ts`, with one change: `MAX_RECONNECT_ATTEMPTS` becomes a parameter instead of a hardcoded `5`. The existing composable is written for page-scoped widgets (e.g. `LiveScoresView`) where giving up after ~30s and showing "refresh the page" is acceptable — wrong for a background, whole-session presence channel. The presence store passes an effectively unlimited retry count with the same capped exponential backoff (`RECONNECT_DELAYS`), so a temporary network blip doesn't permanently drop a user to "offline" for the rest of their visit.
- Footer component reads the presence store, renders `"{registeredCount} members · {guestCount} guests online"`.
- New admin view/tab: table of registered users from `/admin/users` — display_name, in_game_name, approved, created_at, and an online/offline dot. Fetch-on-mount + manual refresh button, matching the existing admin panel's pattern elsewhere (no separate live WS needed on this page — the admin isn't expected to watch it update in real time to the second).

## Data flow

```
Browser tab loads (any page)
  → App.vue opens presence WS with token (if logged in) or none (guest)
  → backend validates token (fail-open to guest) → PresenceManager.connect()
  → broadcast {registered_count, guest_count} to all sockets
  → frontend presence store updates → footer re-renders

Tab closes / network drops
  → receive_text() raises → finally → PresenceManager.disconnect()
  → broadcast updated counts
  (also: 30s periodic broadcast, independent safety net)

Admin opens Users tab
  → GET /admin/users → UserProfile rows + online flag from PresenceManager.registered
```

## Error handling

- Invalid/expired/missing token on presence WS connect → guest, connection accepted (fail open — see above).
- WS disconnect (any cause) → cleaned up via `try/finally` around the receive loop, same as `live_scores.py`.
- Presence WS connection cap reached → reject with `WS_1008_POLICY_VIOLATION`, same as `live_scores.py`'s `MAX_CONNECTIONS` handling.
- Frontend reconnect never permanently gives up for the presence channel (see above) — page-scoped WS like live-scores keeps its existing 5-attempt cap, this only changes for presence.

## Testing

- Backend: unit tests for `PresenceManager` directly — connect/disconnect/count/`is_online` logic, no WebSocket test harness needed, matches this codebase's existing backend test style (plain pytest, no fixtures beyond what's already used).
- Backend: one integration-style test hitting `/admin/users` to confirm the `online` flag reflects `PresenceManager` state.
- Frontend: manual browser verification per CLAUDE.md's UI-change rule — open the site in two tabs (one logged in, one not), confirm footer counts update live, close a tab and confirm the count drops, confirm the admin Users tab shows the logged-in user as online.
- Infra: after deploying `nginx.conf`, verify `sudo nginx -t` passes and `wss://api.tenniselbowhub.live/api/scores/ws` still upgrades correctly (regression check on the fix, since it also touches the pre-existing live-scores WS route).
