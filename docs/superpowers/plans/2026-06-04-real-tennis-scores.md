# Real Tennis Scores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Real Tennis" sub-tab to the Live Scores page showing live/today's ATP/WTA match scores from SofaScore's public API, proxied and cached by the backend.

**Architecture:** Backend service fetches two SofaScore endpoints on-demand, caches for 30s, and serves a single `/api/real-tennis/scores` endpoint. Frontend polls every 30s and renders matches grouped into Live/Upcoming/Completed sections with a tournament filter row. Tab switcher in `LiveScoresView.vue` toggles between existing TE4 content and the new Real Tennis view.

**Tech Stack:** FastAPI (Python), httpx, Vue 3 + TypeScript, Pinia not needed (view-local state only).

**Spec:** `docs/superpowers/specs/2026-06-04-real-tennis-scores-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| CREATE | `backend/app/services/real_tennis_service.py` | SofaScore fetch, in-memory cache, data transform |
| CREATE | `backend/app/api/endpoints/real_tennis.py` | FastAPI router exposing `/api/real-tennis/scores` |
| MODIFY | `backend/app/api/router.py` | Mount real_tennis router |
| CREATE | `backend/tests/test_real_tennis.py` | Unit + integration tests |
| CREATE | `frontend/src/composables/useRealTennis.ts` | TypeScript types + fetch + 30s polling |
| CREATE | `frontend/src/components/real-tennis/RealMatchCard.vue` | Single match display card |
| CREATE | `frontend/src/components/real-tennis/TournamentCard.vue` | Tournament filter button |
| CREATE | `frontend/src/components/real-tennis/RealTennisScores.vue` | Container: filter row + match sections |
| MODIFY | `frontend/src/views/LiveScoresView.vue` | Add tab switcher, wrap TE4 content in v-if |

---

## Task 1: Backend service — pure data transformation functions

**Files:**
- Create: `backend/app/services/real_tennis_service.py`
- Create: `backend/tests/test_real_tennis.py`

- [ ] **Step 1: Write failing unit tests for `_transform_event` and `_extract_tournaments`**

Create `backend/tests/test_real_tennis.py`:

```python
"""Tests for real tennis service and endpoint."""

from fastapi.testclient import TestClient


class TestTransformEvent:
    def test_live_match(self):
        from app.services.real_tennis_service import _transform_event
        raw = {
            "id": 123,
            "tournament": {
                "id": 1,
                "name": "Wimbledon",
                "category": {"name": "ATP"},
            },
            "roundInfo": {"name": "Quarter-finals"},
            "homeTeam": {"name": "Djokovic"},
            "awayTeam": {"name": "Alcaraz"},
            "homeScore": {"period1": 6, "period2": 7},
            "awayScore": {"period1": 4, "period2": 5},
            "status": {"type": "inprogress"},
            "startTimestamp": 1234567890,
        }
        result = _transform_event(raw)
        assert result["id"] == 123
        assert result["player1"] == "Djokovic"
        assert result["player2"] == "Alcaraz"
        assert result["status"] == "live"
        assert result["score"]["sets"] == [[6, 4], [7, 5]]
        assert result["score"]["current_game"] is None
        assert result["tournament"]["name"] == "Wimbledon"
        assert result["tournament"]["round"] == "Quarter-finals"
        assert result["tournament"]["category"] == "ATP"

    def test_upcoming_match_has_empty_sets(self):
        from app.services.real_tennis_service import _transform_event
        raw = {
            "id": 456,
            "tournament": {"id": 2, "name": "US Open", "category": {"name": "WTA"}},
            "roundInfo": {"name": "Round 1"},
            "homeTeam": {"name": "Swiatek"},
            "awayTeam": {"name": "Gauff"},
            "homeScore": {},
            "awayScore": {},
            "status": {"type": "notstarted"},
            "startTimestamp": 1700000000,
        }
        result = _transform_event(raw)
        assert result["status"] == "upcoming"
        assert result["score"]["sets"] == []

    def test_completed_match(self):
        from app.services.real_tennis_service import _transform_event
        raw = {
            "id": 789,
            "tournament": {"id": 1, "name": "Wimbledon", "category": {"name": "ATP"}},
            "roundInfo": {},
            "homeTeam": {"name": "Federer"},
            "awayTeam": {"name": "Nadal"},
            "homeScore": {"period1": 6, "period2": 3, "period3": 6},
            "awayScore": {"period1": 4, "period2": 6, "period3": 4},
            "status": {"type": "finished"},
            "startTimestamp": 1700000000,
        }
        result = _transform_event(raw)
        assert result["status"] == "completed"
        assert result["score"]["sets"] == [[6, 4], [3, 6], [6, 4]]

    def test_missing_fields_handled_gracefully(self):
        from app.services.real_tennis_service import _transform_event
        raw = {"id": 999, "status": {"type": "notstarted"}}
        result = _transform_event(raw)
        assert result["player1"] == "Unknown"
        assert result["player2"] == "Unknown"
        assert result["score"]["sets"] == []
        assert result["tournament"]["name"] == ""


class TestExtractTournaments:
    def test_groups_by_tournament_id(self):
        from app.services.real_tennis_service import _extract_tournaments
        matches = [
            {"tournament": {"id": 1, "name": "Wimbledon", "category": "ATP", "round": "QF"}},
            {"tournament": {"id": 1, "name": "Wimbledon", "category": "ATP", "round": "QF"}},
            {"tournament": {"id": 2, "name": "US Open", "category": "WTA", "round": "R1"}},
        ]
        result = _extract_tournaments(matches)
        assert len(result) == 2
        wimbledon = next(t for t in result if t["id"] == 1)
        assert wimbledon["match_count"] == 2

    def test_sorted_by_match_count_descending(self):
        from app.services.real_tennis_service import _extract_tournaments
        matches = [
            {"tournament": {"id": 2, "name": "US Open", "category": "WTA", "round": "R1"}},
            {"tournament": {"id": 1, "name": "Wimbledon", "category": "ATP", "round": "QF"}},
            {"tournament": {"id": 1, "name": "Wimbledon", "category": "ATP", "round": "QF"}},
        ]
        result = _extract_tournaments(matches)
        assert result[0]["id"] == 1  # Wimbledon has 2 matches, should be first

    def test_empty_input_returns_empty_list(self):
        from app.services.real_tennis_service import _extract_tournaments
        assert _extract_tournaments([]) == []
```

- [ ] **Step 2: Run tests to confirm they fail with ImportError**

```
cd backend
pytest tests/test_real_tennis.py -v
```

Expected: `ImportError: cannot import name '_transform_event' from 'app.services.real_tennis_service'` (or `ModuleNotFoundError` since the file doesn't exist yet).

- [ ] **Step 3: Implement pure functions in service file**

Create `backend/app/services/real_tennis_service.py`:

```python
"""Real tennis scores service — fetches from SofaScore, caches in memory."""

import asyncio
import time
from datetime import date, datetime, timezone
from typing import Any

import httpx

_SOFASCORE_BASE = "https://api.sofascore.com/api/v1"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
}
_CACHE_TTL = 30  # seconds
_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}


def _transform_event(event: dict) -> dict:
    """Map a raw SofaScore event dict to our internal RealMatch shape."""
    tournament_raw = event.get("tournament") or {}
    category_raw = tournament_raw.get("category") or {}
    round_raw = event.get("roundInfo") or {}
    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}
    status_raw = event.get("status") or {}
    status_type = status_raw.get("type", "")

    period_keys = ["period1", "period2", "period3", "period4", "period5"]
    sets: list[list[int]] = []
    for key in period_keys:
        p1 = home_score.get(key)
        p2 = away_score.get(key)
        if p1 is not None and p2 is not None:
            sets.append([p1, p2])

    if status_type == "inprogress":
        status = "live"
    elif status_type in ("finished", "ended", "afterpens", "awardedwin"):
        status = "completed"
    else:
        status = "upcoming"

    return {
        "id": event.get("id"),
        "player1": (event.get("homeTeam") or {}).get("name", "Unknown"),
        "player2": (event.get("awayTeam") or {}).get("name", "Unknown"),
        "score": {
            "sets": sets,
            "current_game": None,
        },
        "status": status,
        "start_timestamp": event.get("startTimestamp"),
        "tournament": {
            "id": tournament_raw.get("id"),
            "name": tournament_raw.get("name", ""),
            "category": category_raw.get("name", ""),
            "round": round_raw.get("name", ""),
        },
    }


def _extract_tournaments(matches: list[dict]) -> list[dict]:
    """Derive sorted tournament list from a flat list of RealMatch dicts."""
    seen: dict[Any, dict] = {}
    for match in matches:
        t = match["tournament"]
        tid = t["id"]
        if tid not in seen:
            seen[tid] = {**t, "match_count": 0}
        seen[tid]["match_count"] += 1
    return sorted(seen.values(), key=lambda x: x["match_count"], reverse=True)


async def fetch_real_tennis_scores() -> dict:
    """Return cached or freshly fetched real tennis scores from SofaScore."""
    now = time.time()

    if _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL:
        return {**_cache["data"], "stale": False}

    today = date.today().isoformat()
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS, timeout=10.0, follow_redirects=True
        ) as client:
            live_resp, today_resp = await asyncio.gather(
                client.get(f"{_SOFASCORE_BASE}/sport/tennis/events/live"),
                client.get(f"{_SOFASCORE_BASE}/sport/tennis/scheduled-events/{today}"),
            )
            live_resp.raise_for_status()
            today_resp.raise_for_status()
            live_events: list[dict] = live_resp.json().get("events") or []
            today_events: list[dict] = today_resp.json().get("events") or []
    except Exception:
        if _cache["data"] is not None:
            return {**_cache["data"], "stale": True}
        return {
            "live": [],
            "upcoming": [],
            "completed": [],
            "tournaments": [],
            "cached_at": None,
            "stale": True,
        }

    live_ids = {e["id"] for e in live_events}
    live_matches = [_transform_event(e) for e in live_events]

    upcoming: list[dict] = []
    completed: list[dict] = []
    for e in today_events:
        if e.get("id") in live_ids:
            continue
        m = _transform_event(e)
        if m["status"] == "upcoming":
            upcoming.append(m)
        elif m["status"] == "completed":
            completed.append(m)

    all_matches = live_matches + upcoming + completed
    data: dict = {
        "live": live_matches,
        "upcoming": upcoming,
        "completed": completed,
        "tournaments": _extract_tournaments(all_matches),
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache["data"] = data
    _cache["fetched_at"] = now
    return {**data, "stale": False}
```

- [ ] **Step 4: Run tests — expect all 7 to pass**

```
cd backend
pytest tests/test_real_tennis.py -v
```

Expected:
```
PASSED tests/test_real_tennis.py::TestTransformEvent::test_live_match
PASSED tests/test_real_tennis.py::TestTransformEvent::test_upcoming_match_has_empty_sets
PASSED tests/test_real_tennis.py::TestTransformEvent::test_completed_match
PASSED tests/test_real_tennis.py::TestTransformEvent::test_missing_fields_handled_gracefully
PASSED tests/test_real_tennis.py::TestExtractTournaments::test_groups_by_tournament_id
PASSED tests/test_real_tennis.py::TestExtractTournaments::test_sorted_by_match_count_descending
PASSED tests/test_real_tennis.py::TestExtractTournaments::test_empty_input_returns_empty_list
7 passed
```

- [ ] **Step 5: Commit**

```
git add backend/app/services/real_tennis_service.py backend/tests/test_real_tennis.py
git commit -m "feat: real tennis service — transform + cache functions"
```

---

## Task 2: Backend endpoint + router mount

**Files:**
- Create: `backend/app/api/endpoints/real_tennis.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/tests/test_real_tennis.py` (append endpoint test class)

- [ ] **Step 1: Append endpoint tests to `backend/tests/test_real_tennis.py`**

Add this class at the bottom of the existing file:

```python
class TestRealTennisEndpoint:
    def test_endpoint_returns_correct_shape(self, client: TestClient) -> None:
        from unittest.mock import AsyncMock, patch

        mock_data = {
            "live": [],
            "upcoming": [],
            "completed": [],
            "tournaments": [],
            "cached_at": "2026-06-04T12:00:00+00:00",
            "stale": False,
        }
        with patch(
            "app.api.endpoints.real_tennis.fetch_real_tennis_scores",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            response = client.get("/api/real-tennis/scores")

        assert response.status_code == 200
        data = response.json()
        for key in ("live", "upcoming", "completed", "tournaments", "stale"):
            assert key in data
        assert isinstance(data["live"], list)
        assert isinstance(data["upcoming"], list)
        assert isinstance(data["completed"], list)
        assert isinstance(data["tournaments"], list)

    def test_endpoint_propagates_stale_flag(self, client: TestClient) -> None:
        from unittest.mock import AsyncMock, patch

        mock_data = {
            "live": [],
            "upcoming": [],
            "completed": [],
            "tournaments": [],
            "cached_at": None,
            "stale": True,
        }
        with patch(
            "app.api.endpoints.real_tennis.fetch_real_tennis_scores",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            response = client.get("/api/real-tennis/scores")

        assert response.status_code == 200
        assert response.json()["stale"] is True
```

- [ ] **Step 2: Run new tests to confirm they fail (404 — endpoint doesn't exist yet)**

```
cd backend
pytest tests/test_real_tennis.py::TestRealTennisEndpoint -v
```

Expected: both tests fail with `AssertionError` on `assert response.status_code == 200` (actual 404).

- [ ] **Step 3: Create the endpoint file**

Create `backend/app/api/endpoints/real_tennis.py`:

```python
"""Real tennis scores endpoint — proxies SofaScore via cached backend service."""

from fastapi import APIRouter, Request

from app.core.limiter import limiter
from app.services.real_tennis_service import fetch_real_tennis_scores

router = APIRouter(prefix="/real-tennis", tags=["Real Tennis"])


@router.get("/scores", summary="Get real-world tennis scores from SofaScore")
@limiter.limit("60/minute")
async def get_real_tennis_scores(request: Request) -> dict:
    """Return live + today's scheduled ATP/WTA match scores.

    Cached for 30 seconds. Returns stale cache if SofaScore is unreachable.
    """
    return await fetch_real_tennis_scores()
```

- [ ] **Step 4: Mount the router in `backend/app/api/router.py`**

Add `real_tennis` to the import line and include its router:

```python
"""Main API router that aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.endpoints import (
    admin,
    contact,
    guides,
    live_scores,
    match_analysis,
    outfits,
    predictions,
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
```

- [ ] **Step 5: Run all real tennis tests — expect 9 to pass**

```
cd backend
pytest tests/test_real_tennis.py -v
```

Expected:
```
PASSED tests/test_real_tennis.py::TestTransformEvent::test_live_match
PASSED tests/test_real_tennis.py::TestTransformEvent::test_upcoming_match_has_empty_sets
PASSED tests/test_real_tennis.py::TestTransformEvent::test_completed_match
PASSED tests/test_real_tennis.py::TestTransformEvent::test_missing_fields_handled_gracefully
PASSED tests/test_real_tennis.py::TestExtractTournaments::test_groups_by_tournament_id
PASSED tests/test_real_tennis.py::TestExtractTournaments::test_sorted_by_match_count_descending
PASSED tests/test_real_tennis.py::TestExtractTournaments::test_empty_input_returns_empty_list
PASSED tests/test_real_tennis.py::TestRealTennisEndpoint::test_endpoint_returns_correct_shape
PASSED tests/test_real_tennis.py::TestRealTennisEndpoint::test_endpoint_propagates_stale_flag
9 passed
```

- [ ] **Step 6: Run full test suite to catch regressions**

```
cd backend
pytest -v
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```
git add backend/app/api/endpoints/real_tennis.py backend/app/api/router.py backend/tests/test_real_tennis.py
git commit -m "feat: real tennis endpoint at /api/real-tennis/scores"
```

---

## Task 3: Frontend composable + TypeScript types

**Files:**
- Create: `frontend/src/composables/useRealTennis.ts`

- [ ] **Step 1: Create the composable**

Create `frontend/src/composables/useRealTennis.ts`:

```typescript
import { ref, onMounted, onUnmounted } from 'vue'
import { apiUrl } from '@/config/api'

export interface RealTennisScore {
  sets: [number, number][]
  current_game: string | null
}

export interface RealTennisTournament {
  id: number
  name: string
  category: string
  round: string
  match_count: number
}

export interface RealTennisMatch {
  id: number
  player1: string
  player2: string
  score: RealTennisScore
  status: 'live' | 'upcoming' | 'completed'
  start_timestamp: number | null
  tournament: RealTennisTournament
}

interface RealTennisResponse {
  live: RealTennisMatch[]
  upcoming: RealTennisMatch[]
  completed: RealTennisMatch[]
  tournaments: RealTennisTournament[]
  cached_at: string | null
  stale: boolean
}

const POLL_INTERVAL_MS = 30_000

export function useRealTennis() {
  const live = ref<RealTennisMatch[]>([])
  const upcoming = ref<RealTennisMatch[]>([])
  const completed = ref<RealTennisMatch[]>([])
  const tournaments = ref<RealTennisTournament[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const stale = ref(false)

  let pollInterval: ReturnType<typeof setInterval> | null = null

  async function fetchScores() {
    try {
      const res = await fetch(apiUrl('/api/real-tennis/scores'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: RealTennisResponse = await res.json()
      live.value = data.live
      upcoming.value = data.upcoming
      completed.value = data.completed
      tournaments.value = data.tournaments
      stale.value = data.stale
      error.value = null
    } catch {
      error.value = 'Failed to load tennis scores'
    } finally {
      isLoading.value = false
    }
  }

  onMounted(() => {
    isLoading.value = true
    fetchScores()
    pollInterval = setInterval(fetchScores, POLL_INTERVAL_MS)
  })

  onUnmounted(() => {
    if (pollInterval !== null) clearInterval(pollInterval)
  })

  return { live, upcoming, completed, tournaments, isLoading, error, stale, fetchScores }
}
```

- [ ] **Step 2: Type-check**

```
cd frontend
npm run type-check
```

Expected: no errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/composables/useRealTennis.ts
git commit -m "feat: useRealTennis composable with TypeScript types"
```

---

## Task 4: RealMatchCard component

**Files:**
- Create: `frontend/src/components/real-tennis/RealMatchCard.vue`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/real-tennis/RealMatchCard.vue`:

```vue
<script setup lang="ts">
import type { RealTennisMatch } from '@/composables/useRealTennis'

const props = defineProps<{ match: RealTennisMatch }>()

function formatTime(ts: number | null): string {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="real-match-card" :class="{ 'is-live': match.status === 'live' }">
    <!-- Header -->
    <div class="match-header">
      <div class="status-badges">
        <span v-if="match.status === 'live'" class="badge badge-live">
          <span class="live-dot-pulse"></span>
          LIVE
        </span>
        <span v-else-if="match.status === 'upcoming'" class="badge badge-waiting">
          {{ formatTime(match.start_timestamp) }}
        </span>
        <span v-else class="badge badge-finished">✓ Finished</span>

        <span class="badge badge-tournament">{{ match.tournament.name }}</span>
        <span v-if="match.tournament.round" class="badge badge-round">
          {{ match.tournament.round }}
        </span>
      </div>
    </div>

    <!-- Players + scores grid -->
    <div class="match-grid">
      <!-- Player 1 -->
      <div class="player-row">
        <div class="player-info">
          <span class="player-name">{{ match.player1 }}</span>
        </div>
        <div class="sets-column">
          <span
            v-for="(set, i) in match.score.sets"
            :key="i"
            class="set-score"
          >{{ set[0] }}</span>
        </div>
      </div>

      <!-- Player 2 -->
      <div class="player-row">
        <div class="player-info">
          <span class="player-name">{{ match.player2 }}</span>
        </div>
        <div class="sets-column">
          <span
            v-for="(set, i) in match.score.sets"
            :key="i"
            class="set-score"
          >{{ set[1] }}</span>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="match-footer">
      <span class="footer-tag">{{ match.tournament.category }}</span>
    </div>
  </div>
</template>

<style scoped>
.real-match-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  transition: all var(--transition-base);
}

.real-match-card:hover {
  border-color: var(--color-brand-primary);
  box-shadow: var(--shadow-md);
}

.real-match-card.is-live {
  border-left: 4px solid var(--color-brand-live);
}

.match-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-badges {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  flex-wrap: wrap;
}

.badge-live {
  background-color: var(--color-brand-live);
  color: var(--color-text-inverse);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-family: var(--font-heading);
  font-weight: 700;
  font-style: italic;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.live-dot-pulse {
  width: 8px;
  height: 8px;
  background-color: var(--color-surface);
  border-radius: 50%;
  animation: pulse 1.5s infinite ease-in-out;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 255, 255, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }
}

.badge-waiting {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-heading);
  font-weight: 600;
}

.badge-finished {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-muted);
  font-family: var(--font-heading);
  font-weight: 600;
}

.badge-tournament {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 0.75rem;
  max-width: 180px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.badge-round {
  background: var(--color-bg-secondary);
  color: var(--color-text-muted);
  font-size: 0.7rem;
  font-weight: 600;
}

.match-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.player-row {
  display: flex;
  align-items: center;
  min-height: 36px;
}

.player-info {
  flex: 1;
  min-width: 0;
}

.player-name {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.sets-column {
  display: flex;
  gap: 12px;
  margin-left: var(--space-3);
}

.set-score {
  width: 20px;
  text-align: center;
  font-family: var(--font-data);
  font-size: var(--font-size-lg);
  font-weight: 500;
  color: var(--color-text-primary);
}

.match-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
}

.footer-tag {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
</style>
```

- [ ] **Step 2: Type-check**

```
cd frontend
npm run type-check
```

Expected: no errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/components/real-tennis/RealMatchCard.vue
git commit -m "feat: RealMatchCard component for real tennis scores"
```

---

## Task 5: TournamentCard component

**Files:**
- Create: `frontend/src/components/real-tennis/TournamentCard.vue`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/real-tennis/TournamentCard.vue`:

```vue
<script setup lang="ts">
import type { RealTennisTournament } from '@/composables/useRealTennis'

defineProps<{
  tournament: RealTennisTournament
  active: boolean
}>()

defineEmits<{ select: [id: number] }>()
</script>

<template>
  <button
    class="tournament-card"
    :class="{ active }"
    @click="$emit('select', tournament.id)"
  >
    <div class="tournament-name">{{ tournament.name }}</div>
    <div class="tournament-meta">
      <span class="category-badge">{{ tournament.category }}</span>
      <span v-if="tournament.round" class="round-label">{{ tournament.round }}</span>
    </div>
    <div class="match-count">
      {{ tournament.match_count }} match{{ tournament.match_count !== 1 ? 'es' : '' }}
    </div>
  </button>
</template>

<style scoped>
.tournament-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2) var(--space-3);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
  gap: 2px;
  min-width: 120px;
}

.tournament-card:hover {
  border-color: var(--color-brand-primary);
  box-shadow: var(--shadow-md);
}

.tournament-card.active {
  border-color: var(--color-brand-primary);
  background: var(--color-bg-secondary);
}

.tournament-name {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.tournament-meta {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.category-badge {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-brand-live);
}

.round-label {
  font-size: 0.65rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

.match-count {
  font-size: 0.65rem;
  color: var(--color-text-secondary);
  font-weight: 600;
}
</style>
```

- [ ] **Step 2: Type-check**

```
cd frontend
npm run type-check
```

Expected: no errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/components/real-tennis/TournamentCard.vue
git commit -m "feat: TournamentCard filter component"
```

---

## Task 6: RealTennisScores container

**Files:**
- Create: `frontend/src/components/real-tennis/RealTennisScores.vue`

- [ ] **Step 1: Create the container component**

Create `frontend/src/components/real-tennis/RealTennisScores.vue`:

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRealTennis, type RealTennisMatch } from '@/composables/useRealTennis'
import RealMatchCard from './RealMatchCard.vue'
import TournamentCard from './TournamentCard.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { Activity } from 'lucide-vue-next'

const { live, upcoming, completed, tournaments, isLoading, error, stale, fetchScores } = useRealTennis()
const selectedTournamentId = ref<number | null>(null)

function filterByTournament(matches: RealTennisMatch[]): RealTennisMatch[] {
  if (selectedTournamentId.value === null) return matches
  return matches.filter(m => m.tournament.id === selectedTournamentId.value)
}

const filteredLive = computed(() => filterByTournament(live.value))
const filteredUpcoming = computed(() => filterByTournament(upcoming.value))
const filteredCompleted = computed(() => filterByTournament(completed.value))
const hasMatches = computed(
  () => filteredLive.value.length + filteredUpcoming.value.length + filteredCompleted.value.length > 0
)
</script>

<template>
  <div class="real-tennis-scores">
    <!-- Stale data warning -->
    <ErrorAlert
      v-if="stale"
      type="warning"
      message="Score data may be delayed — SofaScore temporarily unreachable"
      :dismissible="false"
    />

    <!-- Tournament filter row -->
    <div v-if="tournaments.length" class="tournament-filter-row">
      <button
        class="all-pill"
        :class="{ active: selectedTournamentId === null }"
        @click="selectedTournamentId = null"
      >
        All
      </button>
      <TournamentCard
        v-for="t in tournaments"
        :key="t.id"
        :tournament="t"
        :active="selectedTournamentId === t.id"
        @select="selectedTournamentId = $event"
      />
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="loading-state">
      <LoadingSpinner size="lg" />
      <p>Loading scores...</p>
    </div>

    <!-- Error state (no data at all) -->
    <ErrorAlert
      v-else-if="error && !hasMatches"
      :message="error"
      type="error"
      @dismiss="fetchScores()"
    />

    <!-- Empty state -->
    <div v-else-if="!hasMatches" class="empty-state">
      <div class="empty-icon-wrapper">
        <Activity :size="64" :stroke-width="1.5" />
      </div>
      <h3>No matches today</h3>
      <p>Check back during a tournament day</p>
    </div>

    <!-- Match sections -->
    <template v-else>
      <div v-if="filteredLive.length" class="match-section">
        <h3 class="section-label">
          <span class="section-dot"></span>
          Live Now
        </h3>
        <div class="matches-grid">
          <RealMatchCard v-for="m in filteredLive" :key="m.id" :match="m" />
        </div>
      </div>

      <div v-if="filteredUpcoming.length" class="match-section">
        <h3 class="section-label">Today's Schedule</h3>
        <div class="matches-grid">
          <RealMatchCard v-for="m in filteredUpcoming" :key="m.id" :match="m" />
        </div>
      </div>

      <div v-if="filteredCompleted.length" class="match-section">
        <h3 class="section-label">Completed</h3>
        <div class="matches-grid">
          <RealMatchCard v-for="m in filteredCompleted" :key="m.id" :match="m" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.real-tennis-scores {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.tournament-filter-row {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-2);
  scrollbar-width: thin;
}

.all-pill {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-base);
}

.all-pill:hover,
.all-pill.active {
  border-color: var(--color-brand-primary);
  color: var(--color-brand-primary);
}

.match-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.section-label {
  font-size: var(--font-size-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.section-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-brand-live);
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
  animation: pulse-green 2s infinite;
}

@keyframes pulse-green {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
}

.matches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
  gap: var(--space-4);
  color: var(--color-text-muted);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
  text-align: center;
}

.empty-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  margin-bottom: var(--space-6);
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
}

[data-theme="dark"] .empty-icon-wrapper {
  color: var(--color-brand-primary);
  background: rgba(212, 255, 95, 0.1);
  box-shadow: 0 0 20px rgba(212, 255, 95, 0.15);
}

.empty-state h3 {
  margin-bottom: var(--space-2);
}

.empty-state p {
  color: var(--color-text-muted);
  max-width: 300px;
}

@media (max-width: 768px) {
  .matches-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 2: Type-check**

```
cd frontend
npm run type-check
```

Expected: no errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/components/real-tennis/RealTennisScores.vue
git commit -m "feat: RealTennisScores container with tournament filter"
```

---

## Task 7: Tab switcher in LiveScoresView

**Files:**
- Modify: `frontend/src/views/LiveScoresView.vue`

The existing page has: page header → MonthlyOverview → FilterBar → match grid → last-updated. We add a tab switcher between the header and MonthlyOverview, then wrap everything TE4-specific in `v-if`.

- [ ] **Step 1: Add the tab ref and import to the `<script setup>` block**

In `frontend/src/views/LiveScoresView.vue`, add `ref` to the existing Vue import and add `RealTennisScores` import. Replace the existing script setup opening lines:

Find:
```typescript
import { onMounted, watch } from 'vue'
```

Replace with:
```typescript
import { onMounted, ref, watch } from 'vue'
import RealTennisScores from '@/components/real-tennis/RealTennisScores.vue'
```

Then add this line after the `const store = useScoresStore()` line:
```typescript
const activeTab = ref<'te4' | 'real'>('te4')
```

- [ ] **Step 2: Add the tab switcher markup and wrap TE4 content**

In the `<template>`, the current structure after `</div>` (end of `.page-header`) is:

```html
    <!-- Monthly Stats & Top Players Section -->
    <MonthlyOverview />

    <!-- Filters -->
    <FilterBar ...
```

Replace everything from `<!-- Monthly Stats -->` through the closing `</div>` of `.live-scores-view` with:

```html
    <!-- Tab switcher -->
    <div class="tab-switcher">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'te4' }"
        @click="activeTab = 'te4'"
      >
        TE4 Live
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'real' }"
        @click="activeTab = 'real'"
      >
        Real Tennis
      </button>
    </div>

    <!-- TE4 content -->
    <template v-if="activeTab === 'te4'">
      <!-- Monthly Stats & Top Players Section -->
      <MonthlyOverview />

      <!-- Filters -->
      <FilterBar
        :filters="store.filters"
        @update:filters="handleFilterUpdate"
        @refresh="handleRefresh"
      />

      <!-- Error state -->
      <ErrorAlert
        v-if="store.error || wsError"
        :message="store.error || wsError"
        type="error"
        @dismiss="store.clearError()"
      />

      <!-- Loading state -->
      <div v-if="store.isLoading && !store.servers.length" class="loading-state">
        <LoadingSpinner size="lg" />
        <p>Loading matches...</p>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!store.filteredServers.length"
        class="empty-state"
      >
        <div class="empty-icon-wrapper">
          <Activity class="empty-icon" :size="64" :stroke-width="1.5" />
        </div>
        <h3>No matches found</h3>
        <p v-if="store.filters.searchQuery || store.filters.surface || store.filters.startedOnly">
          Try adjusting your filters
        </p>
        <p v-else>
          No live matches at the moment. Check back later!
        </p>
      </div>

      <!-- Match grid -->
      <div v-else class="matches-grid">
        <MatchCard
          v-for="server in store.filteredServers"
          :key="server.creation_time_ms"
          :server="server"
        />
      </div>

      <!-- Last updated -->
      <div v-if="store.lastUpdated" class="last-updated">
        Last updated: {{ formatTime(store.lastUpdated) }}
      </div>
    </template>

    <!-- Real Tennis content -->
    <RealTennisScores v-else />
  </div>
```

- [ ] **Step 3: Add tab switcher styles to the `<style scoped>` block**

Add before the closing `</style>` tag:

```css
/* Tab switcher */
.tab-switcher {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.tab-btn {
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-full);
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all var(--transition-base);
  letter-spacing: 0.02em;
}

.tab-btn:hover {
  color: var(--color-text-primary);
  border-color: var(--color-border);
}

.tab-btn.active {
  color: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  background: var(--color-bg-secondary);
}
```

- [ ] **Step 4: Type-check**

```
cd frontend
npm run type-check
```

Expected: no errors.

- [ ] **Step 5: Commit**

```
git add frontend/src/views/LiveScoresView.vue
git commit -m "feat: add TE4 Live / Real Tennis tab switcher to live scores page"
```

---

## Task 8: Local dev server test

Run both servers and verify the feature end-to-end before pushing.

- [ ] **Step 1: Start both servers**

In PowerShell from the project root:
```powershell
./start-dev.ps1
```

Or manually in two terminals:
```
# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

- [ ] **Step 2: Test the backend endpoint directly**

Open a new terminal and run:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/real-tennis/scores" | Select-Object -ExpandProperty Content
```

Or in the browser: `http://localhost:8000/api/real-tennis/scores`

Expected: JSON response with keys `live`, `upcoming`, `completed`, `tournaments`, `cached_at`, `stale`.

If `stale: true` and all arrays empty → SofaScore is unreachable from your machine. Try opening `https://api.sofascore.com/api/v1/sport/tennis/events/live` in a browser to confirm. If it loads there but not in the server, check if httpx is blocked.

- [ ] **Step 3: Test the frontend tab**

Open `http://localhost:5173` → navigate to **Live Scores**.

Checklist:
- [ ] Two tab buttons visible: **TE4 Live** and **Real Tennis**
- [ ] TE4 Live tab is active by default — existing content works unchanged
- [ ] Click **Real Tennis** tab — switches content
- [ ] If tournaments are live today: tournament filter row appears as scrollable cards
- [ ] Match cards appear in Live Now / Today's Schedule / Completed sections
- [ ] Match cards show player names, set scores, tournament name, round
- [ ] If `stale: true`: yellow ⚠️ banner shows at the top of Real Tennis tab
- [ ] If no matches today: empty state with tennis icon and "No matches today"
- [ ] Click back to **TE4 Live** — existing scores/stats work correctly
- [ ] Check mobile viewport (DevTools responsive mode, 375px width): tabs stack cleanly, match cards fill full width

- [ ] **Step 4: Verify 30-second polling**

With DevTools Network tab open, filter by `real-tennis`. Wait ~30 seconds. Confirm a second request fires automatically.

- [ ] **Step 5: Run backend tests one final time**

```
cd backend
pytest -v
```

Expected: all tests pass (no regressions).

- [ ] **Step 6: Run frontend type-check and lint**

```
cd frontend
npm run type-check
npm run lint
```

Expected: no errors.
