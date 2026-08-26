# Clickable Live-Score Player Stats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any logged-in user click a TE4 singles name on Live Scores and see the same player-detail popup as Players DB, scoped to that name’s ELO cluster; guests get a signup prompt instead.

**Architecture:** Pure clustering helpers in `stats_service.py` (sort/split on a 200 ELO gap, pick nearest cluster). New `GET /api/players/{name}?elo=` for any logged-in user. Admin list/CSV switches to `get_player_clusters_async()`. One shared `PlayerDetailsModal` owns fetch + a11y. MatchCard emits `{name, elo}` on singles names only.

**Tech Stack:** FastAPI, SQLAlchemy async, Vue 3 + Pinia, pytest (`asyncio_mode = auto`).

**Spec:** `docs/superpowers/specs/2026-08-25-live-player-stats-popup-design.md`

## Global Constraints

- `ELO_BAND = 200`. Alias map first, then cluster. No new tables / Alembic.
- Do **not** change `get_all_players_async` or `get_top_players_async` signatures or bodies.
- Do **not** rewrite the name-merged `get_player_details_async` loop; when `elo` is set, run that loop then filter/recompute from the subset.
- This repo has **no test-DB isolation**. Do not write tests that execute real `finished_matches` queries. Unit-test helpers with in-memory lists. API tests only hit 401/422/404 (no valid JWT in CI).
- Frontend has **no Vitest files**. Gate with `npm run type-check`. Browser-check at the end.
- Do not extract a shared `getAuthHeaders` helper.
- Do not add `GuestSignupPrompt.vue`.
- Scraper User-Agent and pgbouncer settings are unrelated — do not touch them.

## File map

| File | Role |
|---|---|
| `backend/app/services/stats_service.py` | `ELO_BAND`, `_split_elo_clusters`, `_pick_cluster`, `_details_from_matches`, `empty_player_details`, `cluster_list_rows`, `get_player_clusters_async`, `get_player_details_async(..., elo=None)` |
| `backend/tests/test_player_clusters.py` | Unit tests for helpers (no DB) |
| `backend/app/api/endpoints/players.py` | `GET /api/players/{name:path}?elo=` |
| `backend/app/api/router.py` | Mount players router |
| `backend/app/api/endpoints/admin.py` | List/CSV → clusters; **delete** `GET /players/{player_name}` |
| `backend/tests/test_player_api.py` | Unauthenticated 401/422; deleted admin detail 404 |
| `frontend/src/composables/usePlayerDetails.ts` | Fetch `/api/players/{name}?elo=`, stale-response guard |
| `frontend/src/components/players/PlayerDetailsModal.vue` | Cut from AdminPlayersView; owns fetch/a11y/empty |
| `frontend/src/composables/useAdminPlayers.ts` | `uniquePlayerNames` |
| `frontend/src/views/AdminPlayersView.vue` | Use modal; composite keys; KPI passes elo |
| `frontend/src/components/scores/MatchCard.vue` | Clickable singles names |
| `frontend/src/views/LiveScoresView.vue` | Guest prompt + modal |
| `CLAUDE.md` | Document public player-detail route |

---

### Task 1: ELO cluster helpers (pure, no DB)

**Files:**
- Modify: `backend/app/services/stats_service.py`
- Test: `backend/tests/test_player_clusters.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: module-level `ELO_BAND = 200`; `empty_player_details(name: str) -> dict[str, Any]`; `_split_elo_clusters(matches: list[dict[str, Any]]) -> list[list[dict[str, Any]]]` (each match has `player_elo: int > 0`); `_pick_cluster(clusters: list[list[dict[str, Any]]], elo: int) -> list[dict[str, Any]]`; `_details_from_matches(name: str, matches: list[dict[str, Any]], today: date) -> dict[str, Any]`; `cluster_list_rows(appearances: list[dict[str, Any]]) -> list[dict[str, Any]]` (each appearance: `name`, `player_elo`, `date` as `date \| None`).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_player_clusters.py`:

```python
"""Unit tests for ELO clustering helpers — no database."""

from datetime import date

from app.services.stats_service import (
    ELO_BAND,
    cluster_list_rows,
    empty_player_details,
    _details_from_matches,
    _pick_cluster,
    _split_elo_clusters,
)


def _m(elo: int, result: str = "W", day: str | None = "2026-08-01", opponent_elo: int = 1500) -> dict:
    return {
        "opponent": "X",
        "score": "6/4",
        "date": day,
        "player_elo": elo,
        "opponent_elo": opponent_elo,
        "result": result,
    }


def test_elo_band_is_200():
    assert ELO_BAND == 200


def test_split_two_disjoint_groups():
    matches = [_m(1200), _m(1220), _m(2100), _m(2120)]
    clusters = _split_elo_clusters(matches)
    elos = [sorted(m["player_elo"] for m in c) for c in clusters]
    assert elos == [[1200, 1220], [2100, 2120]]


def test_split_climber_stays_one_cluster():
    matches = [_m(e) for e in (1200, 1400, 1600, 1800, 2000, 2100)]
    clusters = _split_elo_clusters(matches)
    assert len(clusters) == 1
    assert len(clusters[0]) == 6


def test_split_gap_exactly_200_stays_connected():
    # 1200 and 1400 differ by 200 → same cluster
    clusters = _split_elo_clusters([_m(1200), _m(1400)])
    assert len(clusters) == 1


def test_split_gap_201_splits():
    clusters = _split_elo_clusters([_m(1200), _m(1401)])
    assert len(clusters) == 2


def test_pick_cluster_by_live_elo():
    low = [_m(1200), _m(1220)]
    high = [_m(2100), _m(2120)]
    clusters = [low, high]
    picked = _pick_cluster(clusters, 2110)
    assert {m["player_elo"] for m in picked} == {2100, 2120}
    picked_low = _pick_cluster(clusters, 1210)
    assert {m["player_elo"] for m in picked_low} == {1200, 1220}


def test_pick_cluster_empty_when_far():
    clusters = [_split_elo_clusters([_m(2100), _m(2120)])[0]]
    assert _pick_cluster(clusters, 1200) == []


def test_pick_cluster_tie_prefers_more_matches():
    a = [_m(1300)]
    b = [_m(1500), _m(1510)]
    # 1400 is 100 from both intervals [1300,1300] and [1500,1510]
    picked = _pick_cluster([a, b], 1400)
    assert len(picked) == 2


def test_cluster_list_rows_splits_same_name():
    rows = cluster_list_rows(
        [
            {"name": "Ambience", "player_elo": 1200, "date": date(2026, 1, 1)},
            {"name": "Ambience", "player_elo": 1220, "date": date(2026, 1, 2)},
            {"name": "Ambience", "player_elo": 2100, "date": date(2026, 2, 1)},
            {"name": "Other", "player_elo": 1500, "date": date(2026, 1, 1)},
        ]
    )
    ambi = [r for r in rows if r["name"] == "Ambience"]
    assert len(ambi) == 2
    elos = sorted(r["latest_elo"] for r in ambi)
    assert elos == [1220, 2100]
    low = next(r for r in ambi if r["latest_elo"] == 1220)
    assert low["total_matches"] == 2
    assert low["last_match_date"] == "2026-01-02"


def test_empty_player_details_has_no_error_key():
    out = empty_player_details("Ambience")
    assert out["name"] == "Ambience"
    assert out["total_matches"] == 0
    assert out["wins"] == 0
    assert out["recent_matches"] == []
    assert "error" not in out


def test_details_from_matches_recomputes_wl():
    matches = [
        _m(2100, "W", "2026-08-20", 2200),
        _m(2080, "L", "2026-08-10", 1000),
        _m(2090, "W", "2026-07-01", 1800),
    ]
    out = _details_from_matches("Ambience", matches, today=date(2026, 8, 25))
    assert out["wins"] == 2
    assert out["losses"] == 1
    assert out["total_matches"] == 3
    assert out["win_rate"] == 66.7
    assert out["matches_last_7_days"] == 1
    assert out["matches_last_30_days"] == 2
    assert out["best_win"]["opponent_elo"] == 2200
    assert out["worst_loss"]["opponent_elo"] == 1000
    assert len(out["recent_matches"]) == 3
    assert "error" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:

```bash
pytest tests/test_player_clusters.py -v
```

Expected: FAIL — `ImportError` or `cannot import name`.

- [ ] **Step 3: Add helpers as module-level functions** (not methods)

Place them in `stats_service.py` **after the `StatsService` class ends** (after `get_player_details_async` / the `except` that returns `{"error": ...}`) and **before** `# Singleton instance` / `_stats_service`. Tests import these names from the module. Do **not** put them after `_resolve_name` inside the class — that would make them methods and break `from app.services.stats_service import _split_elo_clusters`.

```python
ELO_BAND = 200


def empty_player_details(name: str) -> dict[str, Any]:
    """Cluster miss / no rated matches — never include `error`."""
    return {
        "name": name,
        "total_matches": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0,
        "matches_last_7_days": 0,
        "matches_last_30_days": 0,
        "best_win": None,
        "worst_loss": None,
        "recent_matches": [],
    }


def _split_elo_clusters(matches: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    rated = [m for m in matches if m.get("player_elo") and m["player_elo"] > 0]
    if not rated:
        return []
    ordered = sorted(rated, key=lambda m: m["player_elo"])
    clusters: list[list[dict[str, Any]]] = [[ordered[0]]]
    for match in ordered[1:]:
        if match["player_elo"] - clusters[-1][-1]["player_elo"] > ELO_BAND:
            clusters.append([match])
        else:
            clusters[-1].append(match)
    return clusters


def _cluster_interval_distance(elo: int, cluster: list[dict[str, Any]]) -> int:
    elos = [m["player_elo"] for m in cluster]
    lo, hi = min(elos), max(elos)
    if lo <= elo <= hi:
        return 0
    if elo < lo:
        return lo - elo
    return elo - hi


def _parse_match_date(raw: object) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _latest_in_cluster(
    cluster: list[dict[str, Any]],
) -> tuple[dict[str, Any], date | None]:
    dated_ok: list[tuple[dict[str, Any], date]] = []
    for app in cluster:
        parsed = _parse_match_date(app.get("date"))
        if parsed is not None:
            dated_ok.append((app, parsed))
    if dated_ok:
        return max(dated_ok, key=lambda pair: pair[1])
    return cluster[-1], None


def _cluster_latest_elo(cluster: list[dict[str, Any]]) -> int:
    latest, _ = _latest_in_cluster(cluster)
    return int(latest["player_elo"])


def _pick_cluster(clusters: list[list[dict[str, Any]]], elo: int) -> list[dict[str, Any]]:
    if not clusters:
        return []
    ranked = sorted(
        clusters,
        key=lambda c: (
            _cluster_interval_distance(elo, c),
            -len(c),
            -_cluster_latest_elo(c),
        ),
    )
    best = ranked[0]
    if _cluster_interval_distance(elo, best) > ELO_BAND:
        return []
    return best


def _details_from_matches(
    name: str, matches: list[dict[str, Any]], today: date
) -> dict[str, Any]:
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    ordered = sorted(
        matches,
        key=lambda m: _parse_match_date(m.get("date")) or date.min,
        reverse=True,
    )
    wins = 0
    losses = 0
    best_win: dict[str, Any] | None = None
    worst_loss: dict[str, Any] | None = None
    matches_last_7 = 0
    matches_last_30 = 0
    for match_entry in ordered:
        result = match_entry.get("result")
        opponent_elo = match_entry.get("opponent_elo")
        if result == "W":
            wins += 1
            if opponent_elo and opponent_elo > 0:
                if best_win is None or opponent_elo > (best_win.get("opponent_elo") or 0):
                    best_win = match_entry
        elif result == "L":
            losses += 1
            if opponent_elo and opponent_elo > 0:
                if worst_loss is None or opponent_elo < (worst_loss.get("opponent_elo") or 9999):
                    worst_loss = match_entry
        match_day = _parse_match_date(match_entry.get("date"))
        if match_day:
            if match_day >= week_ago:
                matches_last_7 += 1
            if match_day >= month_ago:
                matches_last_30 += 1
    completed = wins + losses
    return {
        "name": name,
        "total_matches": completed,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / completed * 100, 1) if completed > 0 else 0,
        "matches_last_7_days": matches_last_7,
        "matches_last_30_days": matches_last_30,
        "best_win": best_win,
        "worst_loss": worst_loss,
        "recent_matches": ordered[:10],
    }


def cluster_list_rows(appearances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (canonical name, ELO cluster). total_matches = appearance count."""
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in appearances:
        by_name.setdefault(row["name"], []).append(row)
    out: list[dict[str, Any]] = []
    for name, apps in by_name.items():
        for cluster in _split_elo_clusters(apps):
            latest_app, latest_day = _latest_in_cluster(cluster)
            out.append(
                {
                    "name": name,
                    "latest_elo": latest_app["player_elo"],
                    "total_matches": len(cluster),
                    "last_match_date": latest_day.isoformat() if latest_day else None,
                }
            )
    out.sort(key=lambda r: r["total_matches"], reverse=True)
    return out
```

`datetime` and `date` are already imported in `stats_service.py`. Keep the `isinstance(raw, datetime)` check **before** `isinstance(raw, date)` — `datetime` is a subclass of `date`.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_player_clusters.py -v
```

Expected: PASS. If `test_pick_cluster_tie_prefers_more_matches` fails, check distances: 1400→1300 is 100, 1400→1500 is 100; `-len` should pick `b`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/stats_service.py backend/tests/test_player_clusters.py
git commit -m "feat: add ELO cluster helpers for player stats identity"
```

---

### Task 2: Wire clustering into stats_service methods

**Files:**
- Modify: `backend/app/services/stats_service.py` (`get_player_details_async`, add `get_player_clusters_async`)

**Interfaces:**
- Consumes: helpers from Task 1.
- Produces: `async def get_player_details_async(self, player_name: str, elo: int | None = None) -> dict[str, Any]`; `async def get_player_clusters_async(self) -> list[dict[str, Any]]`.

- [ ] **Step 1: Change `get_player_details_async` signature and add the elo branch at the end of the successful path, immediately before the existing `return { ... }`**

Do not rewrite the loop. After `matches` / `wins` / etc. are built, add:

```python
                if elo is not None:
                    rated = [
                        m for m in matches
                        if m.get("player_elo") and m["player_elo"] > 0
                    ]
                    chosen = _pick_cluster(_split_elo_clusters(rated), elo)
                    if not chosen:
                        return empty_player_details(player_name)
                    return _details_from_matches(
                        player_name, chosen, self._get_today()
                    )

                completed_matches = wins + losses
                return {
                    # existing dict unchanged
```

And the def line:

```python
    async def get_player_details_async(
        self, player_name: str, elo: int | None = None
    ) -> dict[str, Any]:
```

- [ ] **Step 2: Add `get_player_clusters_async` next to `get_all_players_async`**

Copy the scan from `get_all_players_async` (same select, same `< 5` games filter, same Unknown / `1210967164` / `[.` skips, same `" vs "` split + fallback). **Do not edit `get_all_players_async`.** Instead of Counter/latest overwrite, append appearances with `player_elo > 0`, then `return cluster_list_rows(appearances)`.

```python
    async def get_player_clusters_async(self) -> list[dict[str, Any]]:
        """One row per (canonical name, ELO cluster) for the admin table/CSV."""
        try:
            alias_map = await self._load_alias_map()
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(
                        FinishedMatch.match_name,
                        FinishedMatch.p1_elo,
                        FinishedMatch.p2_elo,
                        FinishedMatch.date,
                        FinishedMatch.score,
                    ).order_by(FinishedMatch.created_at.asc())
                )
                match_records = result.all()

            appearances: list[dict[str, Any]] = []

            def _is_real(n: str) -> bool:
                return bool(n) and n != "Unknown" and n != "1210967164" and not n.startswith("[.")

            def _enough_games(score: str | None) -> bool:
                total_games = 0
                if score:
                    for s in score.split():
                        if "/" in s:
                            parts = s.split("/")
                            g1_str = "".join(c for c in parts[0] if c.isdigit())
                            g2_str = "".join(
                                c for c in parts[1].split("(")[0] if c.isdigit()
                            )
                            if g1_str and g2_str:
                                try:
                                    total_games += int(g1_str) + int(g2_str)
                                except ValueError:
                                    pass
                return total_games >= self.MIN_GAMES_THRESHOLD

            for row in match_records:
                name = row.match_name
                if not name or not _enough_games(row.score):
                    continue
                if " vs " in name:
                    p1, p2 = name.split(" vs ", 1)
                    p1 = self._resolve_name(p1.strip(), alias_map)
                    p2 = self._resolve_name(p2.strip(), alias_map)
                    if _is_real(p1) and row.p1_elo is not None and row.p1_elo > 0:
                        appearances.append(
                            {"name": p1, "player_elo": row.p1_elo, "date": row.date}
                        )
                    if _is_real(p2) and row.p2_elo is not None and row.p2_elo > 0:
                        appearances.append(
                            {"name": p2, "player_elo": row.p2_elo, "date": row.date}
                        )
                else:
                    resolved = self._resolve_name(name.strip(), alias_map)
                    if _is_real(resolved) and row.p1_elo is not None and row.p1_elo > 0:
                        appearances.append(
                            {
                                "name": resolved,
                                "player_elo": row.p1_elo,
                                "date": row.date,
                            }
                        )
            return cluster_list_rows(appearances)
        except Exception as e:
            logger.error(f"Failed to fetch player clusters: {e}")
            return []
```

Nested `_enough_games` duplicates the existing games parser — acceptable here; do not refactor `get_all_players_async` to share it.

- [ ] **Step 3: Re-run helper tests (must still pass)**

```bash
pytest tests/test_player_clusters.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/stats_service.py
git commit -m "feat: cluster player details and admin list rows by ELO"
```

---

### Task 3: Public detail endpoint; drop admin detail; cluster admin list

**Files:**
- Create: `backend/app/api/endpoints/players.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/api/endpoints/admin.py`
- Test: `backend/tests/test_player_api.py`

**Interfaces:**
- Consumes: `get_player_details_async(name, elo)`, `get_player_clusters_async()`.
- Produces: `GET /api/players/{player_name:path}?elo=` (`elo: int` Query `ge=1`), `get_current_user`, limiter `30/minute`. Admin `GET /api/admin/players` and `/csv` call `get_player_clusters_async()`. `GET /api/admin/players/{name}` **removed**.

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_player_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_player_details_unauthenticated():
    response = client.get("/api/players/Ambience", params={"elo": 2100})
    assert response.status_code in (401, 422)


def test_player_details_missing_elo_is_422():
    # Required query param — FastAPI 422 before auth.
    response = client.get("/api/players/Ambience")
    assert response.status_code == 422


def test_admin_player_detail_route_is_gone():
    response = client.get("/api/admin/players/Ambience")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests — they must fail until the new route exists and the admin detail route is deleted**

`GET /api/players/...` is currently 404 (not 401/422). `GET /api/admin/players/Ambience` still exists (200/401/403), so `test_admin_player_detail_route_is_gone` fails. After Step 5, unauthenticated `/api/players/...` matches `test_profile_api.py`: **422** if the `Authorization` header is omitted (`Header()` is required), **401** if a bad `Bearer` token is sent.

```bash
pytest tests/test_player_api.py -v
```

- [ ] **Step 3: Create `backend/app/api/endpoints/players.py`**

```python
"""Logged-in player detail (ELO-clustered)."""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_current_user
from app.core.limiter import limiter

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/{player_name:path}")
@limiter.limit("30/minute")
async def get_player_details(
    request: Request,
    player_name: str,
    elo: int = Query(..., ge=1),
    _user: Any = Depends(get_current_user),
) -> dict:
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_player_details_async(player_name, elo=elo)
```

- [ ] **Step 4: Mount in `backend/app/api/router.py`**

Add `players` to the import from `app.api.endpoints` and `api_router.include_router(players.router)` (next to `admin`).

If `app.api.endpoints` is a package without re-exports, follow existing style: `from app.api.endpoints import admin, ..., players` — add `players` to that list. The current file imports named modules; add `players` the same way.

- [ ] **Step 5: In `admin.py`**

Replace both `get_all_players_async()` calls in `get_all_players` and `get_all_players_csv` with `get_player_clusters_async()`.

Delete the entire `get_player_details` route (`GET /players/{player_name:path}` through its `return await stats_service.get_player_details_async(player_name)`).

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_player_api.py tests/test_player_clusters.py tests/test_admin_users.py tests/test_profile_api.py -v
```

Expected: PASS. Profile tests must still 401/422 (unchanged). Admin detail 404.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/endpoints/players.py backend/app/api/router.py backend/app/api/endpoints/admin.py backend/tests/test_player_api.py
git commit -m "feat: add logged-in player details endpoint and clustered admin list"
```

---

### Task 4: Point `usePlayerDetails` at the new endpoint

**Files:**
- Modify: `frontend/src/composables/usePlayerDetails.ts`

**Interfaces:**
- Consumes: `GET /api/players/{name}?elo=`.
- Produces: `fetchPlayerDetails(playerName: string, elo: number): Promise<void>` with request-id stale guard; 401 → `Session expired — log in again.`

- [ ] **Step 1: Replace `fetchPlayerDetails` and `clearDetails` as follows** (keep `getAuthHeaders` and refs)

```typescript
  let requestId = 0

  async function fetchPlayerDetails(playerName: string, elo: number): Promise<void> {
    const thisRequest = ++requestId
    isLoading.value = true
    error.value = null
    details.value = null

    try {
      const headers = await getAuthHeaders()
      const response = await fetch(
        apiUrl(`/api/players/${encodeURIComponent(playerName)}?elo=${elo}`),
        { headers }
      )

      if (thisRequest !== requestId) return

      if (response.status === 401) {
        throw new Error('Session expired — log in again.')
      }
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`)
      }

      details.value = await response.json()
    } catch (e: any) {
      if (thisRequest !== requestId) return
      error.value = e.message
      console.error('Failed to fetch player details:', e)
    } finally {
      if (thisRequest === requestId) {
        isLoading.value = false
      }
    }
  }

  function clearDetails(): void {
    requestId++
    details.value = null
    error.value = null
    isLoading.value = false
  }
```

- [ ] **Step 2: Do not type-check or commit this file alone.** `AdminPlayersView` still calls `fetchPlayerDetails(playerName)` with one argument. Implement Task 5 in the same change set and make **one** commit at the end of Task 5.

---

### Task 5: Extract `PlayerDetailsModal` and switch AdminPlayersView

**Files:**
- Create: `frontend/src/components/players/PlayerDetailsModal.vue`
- Modify: `frontend/src/composables/usePlayerDetails.ts` (Task 4 — same commit)
- Modify: `frontend/src/views/AdminPlayersView.vue`
- Modify: `frontend/src/composables/useAdminPlayers.ts`

**Interfaces:**
- Consumes: `usePlayerDetails().fetchPlayerDetails(name, elo)`.
- Produces: `<PlayerDetailsModal :open :name :elo @close />`. `useAdminPlayers` also produces `uniquePlayerNames: ComputedRef<string[]>`.

- [ ] **Step 1: Add `uniquePlayerNames` in `useAdminPlayers.ts` after `cleanPlayers`**

```typescript
  const uniquePlayerNames = computed(() =>
    [...new Set(cleanPlayers.value.map(p => p.name))].sort((a, b) =>
      a.localeCompare(b)
    )
  )
```

Export it in the return object next to `allPlayers`.

- [ ] **Step 2: Create `PlayerDetailsModal.vue`**

Cut overlay CSS from AdminPlayersView (the block labeled `/* ─── Player Detail Modal ─── */`, `.modal-overlay` through `.recent-date`). **Do not** move the whole `@media (max-width: 768px)` block — that also styles the toolbar, table, KPIs, and mapper. Only copy the three rules `.player-modal`, `.detail-stats-grid`, `.highlight-match` from inside that media query into **this** component’s own `@media (max-width: 768px)`.

Overlay: keep both `modal-overlay` and `player-details-overlay`. Put the tall-dialog overrides (`align-items: flex-start`, `overflow-y: auto`, `padding: var(--space-8) var(--space-4)`) on `.player-details-overlay` so they win over the global centered `.modal-overlay` in `components.css`. A11y uses `#player-details-dialog`, not the extra class.

```vue
<script setup lang="ts">
import { watch, toRef } from 'vue'
import { usePlayerDetails } from '@/composables/usePlayerDetails'
import { useModalAccessibility } from '@/composables/useModalAccessibility'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { X, Trophy, Target, BarChart3, Hash, Calendar, Activity } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  name: string
  elo: number
}>()

const emit = defineEmits<{ close: [] }>()

const {
  details: playerDetails,
  isLoading: playerDetailsLoading,
  error: playerDetailsError,
  fetchPlayerDetails,
  clearDetails,
} = usePlayerDetails()

useModalAccessibility(toRef(props, 'open'), {
  onClose: () => emit('close'),
  containerSelector: '#player-details-dialog',
})

watch(
  () => [props.open, props.name, props.elo] as const,
  ([open, playerName, elo]) => {
    if (!open || !elo || elo <= 0) {
      clearDetails()
      return
    }
    fetchPlayerDetails(playerName, elo)
  }
)

function formatDate(isoString: string | null): string {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>

<template>
  <div
    v-if="open"
    id="player-details-dialog"
    class="modal-overlay player-details-overlay"
    role="dialog"
    aria-modal="true"
    aria-label="Player details"
    @click.self="emit('close')"
  >
    <div class="player-modal">
      <div class="player-modal-header">
        <h2>{{ playerDetails?.name || name }}</h2>
        <button class="modal-close" aria-label="Close" @click="emit('close')">
          <X :size="20" />
        </button>
      </div>

      <div v-if="playerDetailsLoading" class="modal-loading">
        <LoadingSpinner size="md" />
        <p>Loading player data…</p>
      </div>

      <div v-else-if="playerDetailsError" class="modal-error">
        <p>{{ playerDetailsError }}</p>
      </div>

      <div
        v-else-if="!playerDetails || playerDetails.total_matches === 0"
        class="modal-error"
      >
        <p>No recorded matches yet.</p>
      </div>

      <div v-else-if="playerDetails" class="player-modal-body">
          <div class="detail-stats-grid">
            <div class="detail-stat">
              <Trophy :size="18" class="detail-stat-icon win" />
              <div class="detail-stat-content">
                <span class="detail-stat-value">{{ playerDetails.wins }}</span>
                <span class="detail-stat-label">Wins</span>
              </div>
            </div>
            <div class="detail-stat">
              <Target :size="18" class="detail-stat-icon loss" />
              <div class="detail-stat-content">
                <span class="detail-stat-value">{{ playerDetails.losses }}</span>
                <span class="detail-stat-label">Losses</span>
              </div>
            </div>
            <div class="detail-stat">
              <BarChart3 :size="18" class="detail-stat-icon rate" />
              <div class="detail-stat-content">
                <span class="detail-stat-value">{{ playerDetails.win_rate }}%</span>
                <span class="detail-stat-label">Win Rate</span>
              </div>
            </div>
            <div class="detail-stat">
              <Hash :size="18" class="detail-stat-icon total" />
              <div class="detail-stat-content">
                <span class="detail-stat-value">{{ playerDetails.total_matches }}</span>
                <span class="detail-stat-label">Total</span>
              </div>
            </div>
          </div>
          <div class="detail-section">
            <h3><Activity :size="16" /> Recent Activity</h3>
            <div class="activity-pills">
              <span class="activity-pill">
                <strong>{{ playerDetails.matches_last_7_days }}</strong> matches last 7 days
              </span>
              <span class="activity-pill">
                <strong>{{ playerDetails.matches_last_30_days }}</strong> matches last 30 days
              </span>
            </div>
          </div>
          <div class="detail-section" v-if="playerDetails.best_win">
            <h3><Trophy :size="16" /> Best Win</h3>
            <div class="highlight-match win-highlight">
              <span class="match-result-badge W">W</span>
              <div class="match-info">
                <span class="match-opponent">vs {{ playerDetails.best_win.opponent }}</span>
                <span class="match-score">{{ playerDetails.best_win.score }}</span>
              </div>
              <span class="match-elo" v-if="playerDetails.best_win.opponent_elo">ELO {{ playerDetails.best_win.opponent_elo }}</span>
              <span class="match-date" v-if="playerDetails.best_win.date">{{ formatDate(playerDetails.best_win.date) }}</span>
            </div>
          </div>
          <div class="detail-section" v-if="playerDetails.worst_loss">
            <h3><Target :size="16" /> Worst Loss</h3>
            <div class="highlight-match loss-highlight">
              <span class="match-result-badge L">L</span>
              <div class="match-info">
                <span class="match-opponent">vs {{ playerDetails.worst_loss.opponent }}</span>
                <span class="match-score">{{ playerDetails.worst_loss.score }}</span>
              </div>
              <span class="match-elo" v-if="playerDetails.worst_loss.opponent_elo">ELO {{ playerDetails.worst_loss.opponent_elo }}</span>
              <span class="match-date" v-if="playerDetails.worst_loss.date">{{ formatDate(playerDetails.worst_loss.date) }}</span>
            </div>
          </div>
          <div class="detail-section" v-if="playerDetails.recent_matches?.length">
            <h3><Calendar :size="16" /> Last {{ playerDetails.recent_matches.length }} Matches</h3>
            <div class="recent-matches-list">
              <div class="recent-match" v-for="(match, i) in playerDetails.recent_matches" :key="i">
                <span class="match-result-badge" :class="match.result">{{ match.result }}</span>
                <span class="recent-opponent">{{ match.opponent }}</span>
                <span class="recent-score">{{ match.score ?? '—' }}</span>
                <span class="recent-elo" v-if="match.opponent_elo">{{ match.opponent_elo }}</span>
                <span class="recent-date">{{ formatDate(match.date) }}</span>
              </div>
            </div>
          </div>
      </div>
    </div>
  </div>
</template>

```

After the template, scoped CSS: paste the cut Player Detail Modal block, but **rename** the copied `.modal-overlay { ... }` rules to `.player-details-overlay` (do not also keep a local `.modal-overlay` — that would duplicate the global overlay). Keep `.player-modal` through `.recent-date` as they are.

Empty state: `elo ≤ 0`, skipped fetch, or `total_matches === 0` → **only** “No recorded matches yet.” (not a zeroed stat grid). Do **not** invent a local `emptyDetails` payload — `clearDetails()` plus the `!playerDetails` branch is enough. Copy `formatDate` from AdminPlayersView (table still needs its own copy; do not extract a util).

- [ ] **Step 3: AdminPlayersView wiring**

Remove `usePlayerDetails`, `useModalAccessibility` for the player modal, `showPlayerModal` fetch/clear, and the inlined modal template.

Add `uniquePlayerNames` to the existing `useAdminPlayers()` destructure (next to `allPlayers`). Keep `showPlayerModal`. Add `modalName` / `modalElo` and change `openPlayerModal` to take elo:

```typescript
import PlayerDetailsModal from '@/components/players/PlayerDetailsModal.vue'

const {
  players,
  allPlayers,
  uniquePlayerNames,
  // ...existing fields unchanged...
} = useAdminPlayers()

const showPlayerModal = ref(false)
const modalName = ref('')
const modalElo = ref(0)

function openPlayerModal(playerName: string, elo: number | null) {
  modalName.value = playerName
  modalElo.value = elo ?? 0
  showPlayerModal.value = true
}

function closePlayerModal() {
  showPlayerModal.value = false
}
```

KPI:

```html
<div class="kpi-card kpi-highest" @click="highestEloPlayer && openPlayerModal(highestEloPlayer, highestElo)" ...>
<div class="kpi-card kpi-lowest" @click="lowestEloPlayer && openPlayerModal(lowestEloPlayer, lowestElo)" ...>
```

Table:

```html
<tr v-for="(player, index) in players" :key="`${player.name}-${player.latest_elo}`">
  <td class="col-name player-cell player-clickable" @click="openPlayerModal(player.name, player.latest_elo)">
```

Datalists:

```html
<option v-for="name in uniquePlayerNames" :key="name" :value="name" />
```

(both `player-suggestions` and `alias-suggestions`)

At end of template:

```html
<PlayerDetailsModal
  :open="showPlayerModal"
  :name="modalName"
  :elo="modalElo"
  @close="closePlayerModal"
/>
```

Drop lucide imports that only the modal used: `Trophy`, `Target`, `Calendar`, `Activity`. Keep `BarChart3`, `Hash`, and `X` (KPIs + mapper dismiss). Also remove `usePlayerDetails` and the player-modal `useModalAccessibility` call (the extracted modal owns both). Leave `formatDate` — the table date column still uses it.

- [ ] **Step 4: Type-check**

```bash
npm run type-check
```

Expected: PASS.

- [ ] **Step 5: Commit** (include Task 4 file if it was not committed)

```bash
git add frontend/src/composables/usePlayerDetails.ts frontend/src/composables/useAdminPlayers.ts frontend/src/components/players/PlayerDetailsModal.vue frontend/src/views/AdminPlayersView.vue
git commit -m "feat: extract shared player details modal and cluster admin table keys"
```

---

### Task 6: Clickable singles names on MatchCard

**Files:**
- Modify: `frontend/src/components/scores/MatchCard.vue`

**Interfaces:**
- Produces: emit `select-player` with `{ name: string, elo: number }`. Not emitted for doubles (`mode_display` contains `"doubles"` case-insensitive) or a side with `names.length !== 1`.

- [ ] **Step 1: After `defineProps`, add emit + helpers** (script is currently untyped props — keep that style)

```javascript
const emit = defineEmits(['select-player'])

const isSinglesMatch = computed(() => {
  const mode = (props.server.game_info?.mode_display || '').toLowerCase()
  return !mode.includes('doubles')
})

function sideClickable(names) {
  return isSinglesMatch.value && Array.isArray(names) && names.length === 1
}

function onSelectPlayer(name, elo) {
  emit('select-player', { name, elo: typeof elo === 'number' ? elo : 0 })
}
```

- [ ] **Step 2: Replace name spans**

Player 1 (plain `<span>` when not clickable — do **not** use `disabled` buttons; native disabled styling would grey doubles names):

```html
<template v-for="(name, idx) in players.player1" :key="idx">
  <button
    v-if="sideClickable(players.player1)"
    type="button"
    class="player-name clickable"
    @click.stop="onSelectPlayer(name, server.elo)"
  >
    {{ name }}
  </button>
  <span v-else class="player-name">{{ name }}</span>
</template>
```

Player 2: same with `players.player2` and `server.other_elo`.

```css
button.player-name {
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  font: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
  max-width: 100%;
}
button.player-name.clickable:hover,
button.player-name.clickable:focus-visible {
  color: var(--color-accent);
  text-decoration: underline;
}
```

- [ ] **Step 3: Type-check**

```bash
npm run type-check
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/scores/MatchCard.vue
git commit -m "feat: emit player name clicks from singles live match cards"
```

---

### Task 7: Live Scores guest prompt + modal

**Files:**
- Modify: `frontend/src/views/LiveScoresView.vue`

**Interfaces:**
- Consumes: MatchCard `select-player`; `PlayerDetailsModal`; `useAuthStore().user` / `loading`.

- [ ] **Step 1: Script additions**

```typescript
import { useAuthStore } from '@/stores/auth'
import PlayerDetailsModal from '@/components/players/PlayerDetailsModal.vue'
import { useModalAccessibility } from '@/composables/useModalAccessibility'
import { RouterLink } from 'vue-router'

const authStore = useAuthStore()
const showDetails = ref(false)
const detailsName = ref('')
const detailsElo = ref(0)
const showSignupPrompt = ref(false)
const signupPlayerName = ref('')

useModalAccessibility(showSignupPrompt, {
  onClose: () => { showSignupPrompt.value = false },
  containerSelector: '#live-signup-prompt',
})

function onSelectPlayer(payload: { name: string; elo: number }) {
  if (authStore.loading) return
  if (!authStore.user) {
    signupPlayerName.value = payload.name
    showDetails.value = false
    showSignupPrompt.value = true
    return
  }
  showSignupPrompt.value = false
  detailsName.value = payload.name
  detailsElo.value = payload.elo
  showDetails.value = true
}
```

- [ ] **Step 2: Template — MatchCard + overlays** (only on the TE4 matches grid, not Real Tennis)

```html
<MatchCard
  v-for="server in store.filteredServers"
  :key="server.creation_time_ms"
  :server="server"
  @select-player="onSelectPlayer"
/>

<PlayerDetailsModal
  :open="showDetails"
  :name="detailsName"
  :elo="detailsElo"
  @close="showDetails = false"
/>

<div
  v-if="showSignupPrompt"
  id="live-signup-prompt"
  class="modal-overlay"
  role="dialog"
  aria-modal="true"
  aria-label="Sign up to see player stats"
  @click.self="showSignupPrompt = false"
>
  <div class="signup-prompt-card">
    <h2>See stats for {{ signupPlayerName }}</h2>
    <p>Sign up to view wins, losses, and recent matches for this player.</p>
    <div class="signup-prompt-actions">
      <RouterLink to="/signup" class="btn btn-primary">Sign up</RouterLink>
      <RouterLink to="/login" class="btn btn-secondary">Log in</RouterLink>
    </div>
  </div>
</div>
```

`.btn` / `.btn-primary` / `.btn-secondary` already live in `frontend/src/assets/styles/components.css` (GuidesView uses the same pair). Use them — do **not** copy button CSS into LiveScoresView. Only add local rules for `.signup-prompt-card` (padding, `var(--color-surface)`, border, radius) and `.signup-prompt-actions { display: flex; gap: var(--space-3); }` plus `text-decoration: none` on the links. Do not duplicate `.player-modal`. Global `.modal-overlay` is `align-items: center`, which is correct for this short dialog.

- [ ] **Step 3: Type-check**

```bash
npm run type-check
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/LiveScoresView.vue
git commit -m "feat: open player stats or signup prompt from live scores"
```

---

### Task 8: Docs + verification

**Files:**
- Modify: `CLAUDE.md` (Gotchas + New API endpoint / frontend API notes)

- [ ] **Step 1: Update CLAUDE.md**

In Gotchas, keep “Admin players endpoint: returns all players unpaged (~200KB JSON). Admin-only; client filters.” Add: list rows are **one per ELO cluster** (same name may appear twice). Nickname mapper autocomplete uses unique names.

Add: `GET /api/players/{name}?elo=` — any logged-in user, cluster-scoped details. Do not use `/api/admin/players/{name}` (removed).

- [ ] **Step 2: Run backend tests + frontend type-check**

```bash
pytest tests/test_player_clusters.py tests/test_player_api.py tests/test_profile_api.py tests/test_admin_users.py -v
```

From `frontend/`: `npm run type-check`

Expected: PASS.

- [ ] **Step 3: Browser verification** (dev servers via `./start-dev.ps1`)

1. Logged-out `/live`: click a singles name → signup prompt, no network call to `/api/players/`. Doubles names not clickable. Real Tennis tab unchanged.
2. Logged-in non-admin: click a singles name → same popup as Players DB (wins/losses/activity/best/worst/last 10) or “No recorded matches yet.”
3. Admin Players DB: two rows for a disjoint ELO namesake if present; mapper datalist has each name once; highest/lowest ELO KPI opens the matching cluster.
4. Rapid-click two names: popup shows the second player, not a stale first response.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document clustered player stats API"
```

---

## Self-review (spec coverage)

| Spec requirement | Task |
|---|---|
| ELO_BAND 200, sort/split, nearest cluster, no name-only fallback | 1–2 |
| `get_all_players_async` / `get_top_players` untouched | 2 (explicit) |
| Details loop kept; elo filters subset | 2 |
| List `total_matches` = appearances | 1 `cluster_list_rows` |
| `GET /api/players/{name}?elo=` logged-in, ge=1 | 3 |
| Delete admin detail | 3 |
| Admin list/CSV clustered | 3 |
| Shared modal owns fetch/a11y/empty copy | 5 |
| Tall overlay kept | 5 |
| Unique mapper names, table key, KPI elo | 5 |
| Singles-only clickable names | 6 |
| Guest prompt, auth.loading no-op | 7 |
| No frontend test runner | 8 type-check + browser |
| Profile dropdown unchanged | 3 does not touch profile.py |
