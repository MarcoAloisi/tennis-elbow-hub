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
- Players DB **table** splits the same canonical name into multiple rows when ELO clusters are disjoint.
- Nickname / alias mapping stays as it is today (runs **before** clustering). Mapper autocomplete stays **unique names**.

Out of scope:

- Doubles names (Comp Doubles / Coop Doubles, or `/`-split pairs) — not clickable.
- Real Tennis tab.
- Making the full Players DB list, CSV, or nickname mapper available to non-admins.
- Rewriting how `finished_matches` are stored (no new identity table).
- Clustering `get_top_players_async` / Monthly Overview, or profile-page stats.
- Extracting a shared `getAuthHeaders` helper (already copy-pasted in three composables; not this feature).
- A new frontend test runner (this repo has no Vitest/Jest specs today).

## Identity model

A stats identity is **(canonical name, ELO cluster)**, not the nick alone.

Constant: `ELO_BAND = 200`.

1. **Alias map first.** `Ambi` → `Ambience` still consolidates, same `player_aliases` table and mapper UI.
2. **Then cluster (1D split, not union-find).** For that canonical name, collect that player's finished-match ELOs (`player_elo > 0`, same match filters as today). Sort by ELO. Start a new cluster whenever the gap to the previous ELO is `> 200`.
   - Climber 1200 → 1400 → … → 2100 stays **one** cluster (adjacent gaps ≤ 200).
   - 2100 Ambience and 1200 Ambience with a gap `> 200` stay **two** clusters.
   - This is the same result as union-find on a line, with a short loop instead of a disjoint-set structure.
3. **Matches with missing or `≤ 0` ELO** are excluded from clustering and from cluster-scoped details. They still count in name-merged profile stats (`elo` omitted). A name whose recorded matches all lack ELO does **not** appear as a clustered Players DB row.
4. **Cluster fields.** `latest_elo` / `last_match_date` come from the most recent match in the cluster (by match date). `total_matches` is completed W+L in that cluster.
5. **Lookup by a live or row ELO `E`.** Pick clusters where `cluster_min - 200 ≤ E ≤ cluster_max + 200`.
   - None → empty payload (zeros / empty lists, **no `error` field**), HTTP 200.
   - One → that cluster's full stats (not a sliding window around `E`).
   - Two or more (gap between nearby clusters) → nearest cluster, distance = 0 if `E` is inside `[min, max]`, else distance to the nearer edge. Exact tie → more matches, then higher `latest_elo`.
6. **No name-only fallback** when `E` is missing or `0`. Empty payload instead.

Live Scores and the Players DB **popup** use this same identity. Clicking `Ambience` at 2100 on a live card shows the same numbers as clicking the 2100 Ambience **table row**.

## Architecture

### Backend: clustering in `stats_service` only

No new tables. Do **not** add a `clustered=` flag to `get_all_players_async()` — profile (`GET /api/profile/players`) and Monthly Overview callers stay on the current signature. Leave `get_all_players_async` and `get_top_players_async` **untouched**.

Add `get_player_clusters_async()` for the admin table/CSV only (same row shape as today, one row per cluster).

`get_player_details_async(name, elo=None)`:
- `elo` provided → cluster-scoped payload (same keys as today: `name`, `wins`, `losses`, `win_rate`, `total_matches`, `matches_last_7_days`, `matches_last_30_days`, `best_win`, `worst_loss`, `recent_matches`). Do not add unused fields.
- `elo` omitted → today's name-merged behavior (`GET /api/profile/{id}` already calls it this way; it currently does not get `latest_elo` from this method — leave that alone).

Private helpers: `ELO_BAND`, sort/split, and **one** appearance walk shared by `get_player_clusters_async` and `get_player_details_async` only. Do not rewrite the other two scanners in this change.

`get_top_players_async` is **not** clustered.

### Backend: one new detail route, not two

Add `GET /api/players/{name:path}?elo=2100` in a small `app/api/endpoints/players.py` (this repo mounts one router per feature).

- Auth: `get_current_user` (any logged-in account).
- Rate limit: `30/minute`.
- Query `elo` is required, integer, `ge=1`. Frontend does not call this when live/row ELO is missing or `≤ 0`.
- 401 if missing/invalid token.
- 200 with empty stats if no cluster matches.

Remove `GET /api/admin/players/{name}` once `usePlayerDetails` points at `/api/players/…`. It is the only frontend caller today. Leaving it would keep a name-merged admin URL that disagrees with the clustered popup.

`GET /api/admin/players` and `/csv` stay `require_admin` and call `get_player_clusters_async()`.

`GET /api/profile/players` keeps calling `get_all_players_async()`. No dedupe patch.

### Frontend

- **Cut** (do not copy) the Players DB detail modal markup + `.player-modal*` styles into `frontend/src/components/players/PlayerDetailsModal.vue`. Use the global `.modal-overlay` in `components.css` — AdminPlayersView already re-declares that overlay locally; do not take a third copy. Empty state: when `total_matches === 0` **or** live `elo` is missing/`≤ 0`, show **“No recorded matches yet.”** in that same modal. If `elo ≤ 0`, skip the fetch.
- Guest signup prompt is **inline in `LiveScoresView`** (title, two links, close). Do not add `GuestSignupPrompt.vue`. Copy: **See stats for {name}**; they need an account to view wins, losses, and recent matches; primary **Sign up** → `/signup`; secondary **Log in** → `/login`.
- Only one of those two overlays is open at a time. `useModalAccessibility` queries `document.querySelector('[role="dialog"]')` globally — pass a distinct `containerSelector` for whichever overlay is open.
- `usePlayerDetails`: point at `/api/players/{name}?elo=`; `fetchPlayerDetails(playerName, elo)`; 401 message becomes session-expired, not “admin access required”; ignore stale responses with a request-id counter (not AbortController).
- `MatchCard.vue`: singles names are `<button type="button">` styled to match today’s `.player-name` text (reset native button chrome). `@click.stop` emit `select-player` `{ name, elo }` — p1 `server.elo`, p2 `server.other_elo`. Not clickable when `mode_display` contains `"doubles"` (case-insensitive) **or** that side’s parsed list has more than one name (`/` pairs). Real Tennis is a different component — untouched.
- `LiveScoresView.vue`: `useAuthStore().user` for guest vs logged-in (this view does not import auth today). Guest → prompt, no fetch. Logged-in → shared modal + fetch.
- `AdminPlayersView.vue` table: `:key="\`${player.name}-${player.latest_elo}\`"` (today `:key="player.name"` **will break** once two Ambience rows exist). `openPlayerModal(name, elo)` — table rows pass `player.latest_elo`. **KPI cards today call `openPlayerModal(highestEloPlayer)` with name only** — they must pass the matching ELO (`highestElo` / `lowestElo`, already on the composable).
- Nickname mapper `<option>` loops must iterate **unique names**, not clustered rows. Add a `uniquePlayerNames` computed on `useAdminPlayers` (Set of `allPlayers` names) and use that in the two datalists. Mapper save/delete/rename APIs unchanged.
- KPI “total players” / `avgMatchesPlayed` will count **clusters**, not people. Accept that; do not add a second counter.

## Data flow

```
Live Scores, singles name click
  → guest? inline signup prompt (no fetch)
  → logged in? GET /api/players/{name}?elo={liveElo}  + Bearer
       → alias resolve → sort/split clusters → pick by E → popup
       → no cluster / elo 0 → empty popup "No recorded matches yet."

Players DB row click (admin)
  → GET /api/players/{name}?elo={row.latest_elo}  + Bearer
       → same cluster popup

Players DB table / CSV
  → GET /api/admin/players  (get_player_clusters_async)

Profile link dropdown
  → GET /api/profile/players  (unchanged get_all_players_async)
```

## Error handling

- Guest click: never hits the API.
- 401 (expired session): popup “Session expired — log in again.”
- 429 / network: existing popup error string.
- Live ELO missing or `0`: empty-state popup, no name-only fallback.
- Rapid A then B clicks: drop response if it is not the currently open name+elo.

## Testing

Backend (pytest, matching existing `backend/tests/`):

- Same nick, ELOs 1200 and 2100 → two clustered list rows, two different detail payloads.
- Climber 1200→1400→…→2100 → one clustered list row.
- Alias `Ambi` → `Ambience`, then cluster on ELO.
- `GET /api/players/{name}?elo=` without token → 401.
- Admin list/CSV still 403 for non-admin.
- Unmatched ELO → 200 with zeros / empty lists, no `error` key.
- `get_all_players_async()` still unique names; `get_player_clusters_async()` splits; details without `elo` still name-merged.
- `GET /api/admin/players/{name}` is gone (404).

Frontend: no new test framework. Verify in the browser: singles click, doubles not clickable, guest prompt, logged-in popup, duplicate-name rows in Players DB, mapper still unique names, highest/lowest ELO KPI opens the matching cluster.

## Success criteria

- Logged-in user clicks a TE4 singles name on Live Scores and sees the Players DB popup for that ELO cluster.
- Guest click shows the signup/login prompt and does not load stats.
- Doubles and Real Tennis names are not clickable.
- Players DB table shows separate rows for disjoint ELO groups of the same mapped name; a true ELO climber stays one row.
- Alias mapper behavior and unique-name autocomplete are unchanged.
- Full player list / CSV / mapper remain admin-only.
- Profile linking dropdown is still unique canonical names.
