# Live-score clickable player stats — design

Date: 2026-08-25
Branch: `ionos-migration`

## Problem

Live Scores shows player names as static text. Admins can already open a per-player stats popup from Players DB (wins/losses, win rate, activity, best win, worst loss, last 10 matches), but that page and its API are admin-only. Anyone watching a live match has no way to see that same info.

TE4 nicknames are not account-bound. Two people can play as `Ambience` — one at ~2100 ELO, one at ~1200. Name-only lookup would show the wrong career.

## Scope

- TE4 **singles** names on Live Scores are clickable.
- Logged-in users get the **same stats popup** as Players DB, scoped to that player's **ELO cluster**.
- Guests get an on-page prompt to sign up (and a log-in link).
- Players DB list **splits** the same canonical name into multiple rows when ELO clusters are disjoint.
- Nickname / alias mapping stays as it is today (runs **before** clustering).

Out of scope:

- Doubles names (Comp Doubles / Coop Doubles, or `/`-split pairs) — not clickable.
- Real Tennis tab.
- Making the full Players DB list, CSV, or nickname mapper available to non-admins.
- Rewriting how `finished_matches` are stored (no new identity table).
- Clustering stats on public/profile pages (those stay name-merged when `elo` is omitted).
- Visual regression / load-testing the full-table scan.

## Identity model

A stats identity is **(canonical name, ELO cluster)**, not the nick alone.

Constant: `ELO_BAND = 200`.

1. **Alias map first.** `Ambi` → `Ambience` still consolidates, same `player_aliases` table and mapper UI.
2. **Then cluster.** For that canonical name, take finished matches where they are p1 or p2 (same filters as today: drop `< 5` total games, `Unknown`, bot `[.` prefix, the numeric dummy id). Union-find: two of that player's matches connect if both have `player_elo > 0` and `|elo_a - elo_b| ≤ 200`.
   - A climber 1200 → 1400 → … → 2100 stays **one** cluster (the chain connects).
   - 2100 Ambience and 1200 Ambience with no connecting matches stay **two** clusters.
3. **Matches with missing or `≤ 0` ELO** are excluded from clustering and from cluster-scoped details. They still count in name-merged profile stats (`elo` omitted). A name whose recorded matches all lack ELO does **not** appear as a clustered Players DB row.
4. **Cluster fields.** `latest_elo` / `last_match_date` come from the most recent match in the cluster (by match date). `total_matches` is completed W+L in that cluster.
5. **Lookup by a live or row ELO `E`.** Pick clusters where `cluster_min - 200 ≤ E ≤ cluster_max + 200`.
   - None → empty payload (zeros / empty lists), HTTP 200.
   - One → that cluster's full stats (not a sliding window around `E`).
   - Two or more (gap between nearby clusters) → nearest cluster, distance = 0 if `E` is inside `[min, max]`, else distance to the nearer edge. Exact tie → more matches, then higher `latest_elo`.
6. **No name-only fallback** when `E` is missing or `0`. That would reintroduce impersonation. Empty payload instead.

Live Scores and Players DB use this same identity. Clicking `Ambience` at 2100 on a live card shows the same numbers as clicking the 2100 Ambience row in Players DB.

## Architecture

### Backend: clustering in `stats_service`

No new tables. Clustering is in-memory on the existing `finished_matches` scan.

- `get_all_players_async()` returns **one row per cluster**: `{name, latest_elo, total_matches, last_match_date}`. Same name may appear twice with different `latest_elo`.
- `get_player_details_async(name, elo=None)`:
  - `elo` provided → cluster-scoped payload (same shape as today: `name`, `wins`, `losses`, `win_rate`, `total_matches`, `matches_last_7_days`, `matches_last_30_days`, `best_win`, `worst_loss`, `recent_matches`).
  - `elo` omitted → today's name-merged behavior (profile pages).
- Put `ELO_BAND` and cluster helpers next to the existing alias resolve logic in `stats_service.py`.

### Backend: new logged-in detail endpoint

New router `app/api/endpoints/players.py`, mounted in `router.py`:

`GET /api/players/{name:path}?elo=2100`

- Auth: `get_current_user` (any logged-in account, not admin).
- Rate limit: `30/minute` (same as the current admin player routes).
- Path `name` is the raw live / table name (alias resolve happens server-side). Use `:path` so names with slashes still match, same as the existing admin detail route.
- Query `elo` is required, integer.
- 401 if missing/invalid token.
- 200 with empty stats if no cluster matches.

`GET /api/admin/players` and `/csv` stay `require_admin`. They consume clustered `get_all_players_async()`, so CSV also has one row per cluster.

`GET /api/admin/players/{name}` is no longer the frontend's detail URL. Leave it in place as an admin wrapper that calls the same service with an `elo` query param (required), so the admin namespace does not silently keep a name-only backdoor that disagrees with the popup.

`GET /api/profile/players` (account-linking dropdown) must **dedupe** names after clustering so `Ambience` appears once.

### Frontend

- Extract the Players DB detail modal (+ its styles) into `frontend/src/components/players/PlayerDetailsModal.vue`. Both Live Scores and Players DB use it.
- `usePlayerDetails` calls `GET /api/players/{name}?elo=` with the Supabase bearer token. Accept `(playerName, elo)`. Ignore a stale response if the open modal's name+elo has changed.
- `MatchCard.vue`: singles names are buttons (hover underline, focusable). Emit `select-player` with `{ name, elo }` — player 1 uses `server.elo`, player 2 uses `server.other_elo`. Not clickable when `game_info.mode_display` contains `"doubles"` (case-insensitive) **or** a side's parsed name list has more than one entry (`/` pairs).
- `LiveScoresView.vue`: if `auth.user` is set, open the shared modal and fetch; if not, open the signup prompt. No API call for guests.
- Guest prompt: title **See stats for {name}**; copy that they need an account to view wins, losses, and recent matches; primary **Sign up** → `/signup`; secondary **Log in** → `/login`; overlay / close dismisses.
- `AdminPlayersView.vue`: table `:key` is `name + latest_elo` (names are no longer unique). Click passes `latest_elo` into the shared modal. Nickname mapper unchanged.

## Data flow

```
Live Scores, singles name click
  → guest? signup prompt (no fetch)
  → logged in? GET /api/players/{name}?elo={liveElo}  + Bearer
       → alias resolve → find cluster → popup
       → no cluster / elo 0 → empty popup "No recorded matches yet."

Players DB row click (admin)
  → GET /api/players/{name}?elo={row.latest_elo}  + Bearer
       → same cluster popup
```

## Error handling

- Guest click: never hits the API.
- 401 (expired session): popup message “Session expired — log in again.”
- 429 / network: existing popup error string, not a blank card.
- Live ELO missing or `0`: empty-state popup, no name-only fallback.
- Rapid A then B clicks: drop response if it is not the currently open name+elo.

## Testing

Backend:

- Same nick, ELOs 1200 and 2100 → two list rows, two different detail payloads.
- Climber 1200→1400→…→2100 → one list row.
- Alias `Ambi` → `Ambience`, then cluster on ELO.
- `GET /api/players/{name}?elo=` without token → 401.
- Admin list/CSV still 403 for non-admin.
- Unmatched ELO → 200 with zeros / empty lists.
- Profile name dropdown still unique names; details without `elo` still name-merged.

Frontend:

- Singles name click emits `{ name, elo }`; doubles names do not.
- Guest → prompt, no fetch.
- Logged-in → fetch with `elo`; empty copy when `total_matches === 0`.

## Success criteria

- Logged-in user clicks a TE4 singles name on Live Scores and sees the Players DB popup for that ELO cluster.
- Guest click shows the signup/login prompt and does not load stats.
- Doubles and Real Tennis names are not clickable.
- Players DB shows separate rows for disjoint ELO groups of the same mapped name; a true ELO climber stays one row.
- Alias mapper behavior is unchanged.
- Full player list / CSV / mapper remain admin-only.
