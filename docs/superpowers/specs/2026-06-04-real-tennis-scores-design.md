# Real Tennis Scores — Design Spec

**Date:** 2026-06-04  
**Feature:** Real-life tennis scores sub-tab in Live Scores page  
**Scope:** Option B — Live + Today's Schedule + Active Tournament Cards

---

## Overview

Add a "Real Tennis" sub-tab to the existing Live Scores page. The tab displays real-world ATP/WTA match scores sourced from SofaScore's unofficial public API, proxied and cached by the backend. The TE4 Live tab (existing content) is unchanged.

---

## Backend

### New files

- `backend/app/api/endpoints/real_tennis.py` — FastAPI router
- `backend/app/services/real_tennis_service.py` — SofaScore fetch + in-memory cache

### Service: `real_tennis_service.py`

Fetches two SofaScore endpoints on demand:

```
GET https://api.sofascore.com/api/v1/sport/tennis/events/live
GET https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{YYYY-MM-DD}
```

Headers sent: `User-Agent: Mozilla/5.0` (standard browser UA — SofaScore blocks non-browser UAs).

**Caching:** Single in-memory dict `{ data, fetched_at }`. TTL = 30 seconds.  
- Request arrives → if `now - fetched_at < 30s`: return cached data  
- If stale or empty → fetch SofaScore → update cache → return  
- If SofaScore unreachable and cache exists → return stale data with `stale: True`  
- If SofaScore unreachable and no cache → return empty arrays with `stale: True`

**Data transformation:** Raw SofaScore events are mapped to a clean internal shape. Active tournaments are derived by grouping events by `event.tournament.id` — no separate tournament endpoint needed. Current round comes from `event.roundInfo.name`.

### Endpoint: `real_tennis.py`

```
GET /api/real-tennis/scores
```

Response shape:
```json
{
  "live": [RealMatch],
  "upcoming": [RealMatch],
  "completed": [RealMatch],
  "tournaments": [Tournament],
  "cached_at": "2026-06-04T12:00:00Z",
  "stale": false
}
```

`RealMatch` shape:
```json
{
  "id": 12345,
  "player1": "Novak Djokovic",
  "player2": "Carlos Alcaraz",
  "score": {
    "sets": [[6,4],[7,5],[3,2]],
    "current_game": "*3-2"
  },
  "_note": "current_game is null for upcoming/completed matches; sets may be [] for upcoming",
  "status": "live",
  "start_timestamp": 1234567890,
  "tournament": {
    "id": 1,
    "name": "Wimbledon",
    "category": "ATP",
    "round": "Quarter-finals"
  }
}
```

`Tournament` shape:
```json
{
  "id": 1,
  "name": "Wimbledon",
  "category": "ATP",
  "round": "Quarter-finals",
  "match_count": 4
}
```

Rate limit: `@limiter.limit("60/minute")` on the endpoint (project standard).  
Mount in `backend/app/api/router.py`.

---

## Frontend

### New files

```
frontend/src/composables/useRealTennis.ts
frontend/src/components/real-tennis/RealTennisScores.vue
frontend/src/components/real-tennis/TournamentCard.vue
frontend/src/components/real-tennis/RealMatchCard.vue
```

### Tab switcher — `LiveScoresView.vue`

Add two tab pills below the existing page header, above `MonthlyOverview`:

```
[ TE4 Live ]  [ Real Tennis ]
```

Active tab stored in local `ref<'te4' | 'real'>`. All TE4-specific content (`MonthlyOverview`, `FilterBar`, match grid, last-updated line) wrapped in `v-if="activeTab === 'te4'"`. Real Tennis tab mounts `RealTennisScores.vue` via `v-else`. The page header (title, stats, connection pill) remains visible on both tabs.

### Composable: `useRealTennis.ts`

- Fetches `GET /api/real-tennis/scores` using `apiUrl()` helper (project standard)
- Fetches immediately on mount (`onMounted`), then polls every 30s via `setInterval`, cleared on `onUnmounted`
- Exposes: `live`, `upcoming`, `completed`, `tournaments`, `isLoading`, `error`, `stale`
- No auth header needed (public endpoint)

### Component: `RealTennisScores.vue`

- Imports `useRealTennis`
- Holds `selectedTournamentId: number | null` (null = show all)
- Renders:
  1. Horizontal scrollable row of `TournamentCard` components + "All" pill
  2. Filtered match list (`RealMatchCard` per match) — sections for Live, Upcoming, Completed

### Component: `TournamentCard.vue`

Props: `tournament: Tournament`, `active: boolean`  
Displays: tournament name, category badge (ATP/WTA), current round, match count.  
Emits: `select` event with tournament id.  
Styling: matches existing `stats-breakdown` card style — `var(--color-surface)`, `var(--color-border)`, `var(--radius-lg)`, `var(--shadow-sm)`.

### Component: `RealMatchCard.vue`

Props: `match: RealMatch`  
Displays: player names, set scores, status badge.  
- Live: pulsing green dot (same `pulse-green` animation as connection pill)
- Upcoming: time from `start_timestamp`  
- Completed: checkmark, muted style  
Styling: mirrors existing `MatchCard` — same surface, border, padding variables.

### Error / empty states

- `stale: true` → subtle banner using existing `ErrorAlert` component: "Score data may be delayed"
- No data + error → empty state matching existing `.empty-state` pattern with retry button
- Loading → existing `LoadingSpinner` component

---

## Design constraints

- All CSS uses existing design tokens (`--color-*`, `--space-*`, `--radius-*`, `--font-*`)
- Live indicator reuses existing `pulse-green` keyframe animation
- Empty/loading/error states reuse existing components (`LoadingSpinner`, `ErrorAlert`)
- No new design system additions

---

## Data flow

```
SofaScore API (public, unofficial)
  ↓ httpx — on request if cache stale (TTL 30s)
real_tennis_service.py — in-memory cache
  ↓
GET /api/real-tennis/scores (rate-limited, public)
  ↓ fetch + setInterval 30s
useRealTennis.ts
  ↓
RealTennisScores.vue
  ├── TournamentCard.vue (×N)
  └── RealMatchCard.vue (×N, filtered)
```

---

## Out of scope

- Full bracket/draw visualization (can be added later as standalone feature)
- WebSocket for real tennis (polling is sufficient; data source itself is polled)
- Persisting scores to database
- Historical real tennis results
- Player search or linking real players to TE4 player profiles
