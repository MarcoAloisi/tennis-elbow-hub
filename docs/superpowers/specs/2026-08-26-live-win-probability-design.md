# Live win-probability % — design

Date: 2026-08-26
Branch: `ionos-migration`

## Problem

Live Scores shows raw score only — no signal for who is actually likely to win. Want a live-updating win% per player on singles match cards, combining ELO, head-to-head record, recent form, and current match state (sets/games/points/serve), that updates on every scraper poll with no extra frontend requests.

## Scope

- TE4 **singles** matches only (same restriction as the existing player-click feature — doubles' 4-name strings and shared team ELO don't fit an individual-ELO model).
- Backend computes the %, attaches it to the existing WS score broadcast. No new frontend network calls.
- The pre-match component (ELO + H2H + form) is computed **once per match and cached** — none of those inputs change mid-match. Only the live-state recursion (pure math, no DB) reruns every poll tick.
- Score parsing into structured state (sets/games/points/server) is done **once, server-side, for every live match** (singles and doubles) — not gated to singles, and not duplicated in the frontend (see Architecture).

Out of scope:

- Doubles win probability, Real Tennis tab.
- Modeling serve/return skill splits — TE4's feed has no serve stats. A single derived per-point win rate is used, with a flat serve-bonus applied only to the currently in-progress game/tiebreak (see "Serve bonus" under Probability model).
- Multi-worker-safe caching. In-memory, single polling process — same caveat CLAUDE.md already documents for presence tracking and `_previous_matches`.
- Backfilling `surface`/`mod` on existing `finished_matches` rows. New columns are NULL for historical rows; populate going forward only.
- Calibrating blend weights / serve-bonus constant against real outcome data. Initial constants are heuristic, clearly labeled as tunable in code, not fitted.
- A factor-breakdown tooltip ("based on ELO, H2H 3-1, ..."). Just the % bar for v1.
- Fixing the two pre-existing near-duplicate "count total games from score string" blocks in `stats_service.py` (`_enough_games`, and the inline copy in `get_player_details_async`). Not touching that in this feature — `score_parser.py` becomes the canonical implementation going forward, but migrating those two call sites is a separate cleanup.

## Live match state (score parsing)

New `backend/app/services/score_parser.py`. Parses `GameServer.score` (e.g. `"6/3 4/6 1/1 -- 00:40•"`) the same way `MatchCard.vue`'s `scoreDisplay` computed does today, plus a numeric point index needed for the probability math that the frontend never needed:

```python
@dataclass(frozen=True)
class LiveMatchState:
    sets: list[tuple[str, str]]                  # raw display strings, e.g. [("6","3"), ("4","6"), ("1","1")]
    current_points: tuple[str, str] | None        # raw display strings, e.g. ("00", "40"), ("40", "Ad"); None if no current game segment
    current_points_numeric: tuple[int, int] | None  # same game, as plain ints — 0/15/30/40 mapped to 0-3, Ad to leader+1; tiebreak points parsed as raw int()
    server: int | None                            # 1, 2, or None if the `•` marker is missing/ambiguous
    is_tiebreak: bool                             # current_points don't match {0,15,30,40,Ad,A} on either side
    games_per_set: int                            # from GameInfo.games_per_set; 6 if the field is 0 (TE4's "unset" value)

def parse_live_state(score: str, games_per_set: int) -> LiveMatchState | None:
    """Returns None if `score` doesn't split on ' -- ' or has no set segments — caller falls back gracefully."""
```

`current_points_numeric` exists so `win_probability.py` never touches raw score tokens directly — `score_parser.py` stays the single owner of all score-token interpretation, in whichever vocabulary applies (point-table for a normal game, plain integers for a tiebreak). Without this field, the probability module would need its own private token→number mapping — the exact duplication the score_parser split is meant to prevent.

`is_tiebreak` detection is a heuristic (point tokens outside the normal `{0,15,30,40,Ad,A}` set imply raw tiebreak point counts) — verify against real captured TE4 score strings during implementation; if it doesn't hold, `is_tiebreak` defaults `False` and the set-recursion's tiebreak terminal case (below) simply won't trigger, degrading gracefully to "no live adjustment past 6-6" rather than crashing.

This struct is computed for **every** live match, singles and doubles — `MatchCard.vue` drops its own `scoreDisplay` parsing entirely and renders `server.live_state` instead. One implementation, not two.

## Probability model

New `backend/app/services/win_probability.py`. Pure functions, no DB access except `pre_match_probability`'s inputs (fetched once and cached — see Caching).

### Point → game → set → match recursion

- `_race_to_win_prob(p: float, target: int, a: int, b: int) -> float` — probability the player with per-point win rate `p` wins a race to `target` points (win by 2) from score `(a, b)`. Memoized recursion with base cases `a≥target ∧ a-b≥2` (won) / `b≥target ∧ b-a≥2` (lost), and a closed-form tied-at-the-wire case (`p²/(p²+(1-p)²)`) once both sides are within one point of `target` with the margin not yet met — not a fixed-size grid, a recursion with those two terminal conditions.
- `point_to_game_prob(p, a, b) = _race_to_win_prob(p, 4, a, b)` and `point_to_tiebreak_prob(p, a, b) = _race_to_win_prob(p, 7, a, b)` — thin wrappers, same underlying function, so a normal game and a tiebreak are one implementation, not two. `win_probability.py` picks the wrapper (or just `target`) based on `live_state.is_tiebreak`.
- `game_to_set_prob(g: float, games_a: int, games_b: int, games_per_set: int) -> float` — probability of winning the set from game score `(games_a, games_b)`, treating each remaining game as i.i.d. Bernoulli(`g`). **Terminal case at `games_per_set`-all**: resolves via a single Bernoulli(`g`) trial standing in for a *hypothetical, not-yet-reached* tiebreak (TE4 caps at a breaker, so the recursion must terminate there, not run an unbounded ad-set). This approximation applies only when the tiebreak is a future branch of the recursion — see the note below when the match is *already* in a tiebreak right now.
- `set_to_match_prob(s: float, sets_a: int, sets_b: int, sets_to_win: int) -> float` — probability of winning the match from set score, treating each remaining set as i.i.d. Bernoulli(`s`). `sets_to_win` comes from the **existing** `_detect_format()` mapping in `stats_service.py` (`nb_set` → bo1/bo3/bo5 → sets-to-win 1/2/3) — imported, not reimplemented.
- `implied_game_win_rate(s: float) -> float` / `implied_set_win_rate(p0: float, sets_to_win: int) -> float` — binary-search inverses of the above (both are monotonic and continuous in their rate parameter, so the inversion is well-defined). Computed **once per match**, cached alongside `P0` (see Caching) — not re-solved every poll tick.

**Live tiebreak vs. hypothetical future tiebreak — not the same case.** If `live_state.is_tiebreak` is `True`, the match is *actually* inside a tiebreak right now, and its real point score is known (`current_points_numeric`) — that gets `point_to_tiebreak_prob(p, a, b)`, the genuine race-to-7 recursion, not the coin-flip stand-in. The coin-flip approximation in `game_to_set_prob`'s terminal case is only for tiebreaks that *might happen later* in the chain (e.g. computing set-win probability from 4-4, where 6-6 is still three games away) — those get approximated because modeling every hypothetical future tiebreak's point-level dynamics isn't worth the cost. The live orchestration in `win_probability.py` branches on `is_tiebreak` before deciding which of these two paths handles the current game.

### Serve bonus — current game/tiebreak only

A fixed constant (`SERVE_BONUS = 0.08`, heuristic, commented as tunable) is added to the server's per-point rate and subtracted from the returner's, but **only when computing `_race_to_win_prob` for the live, in-progress game or tiebreak**. `game_to_set_prob` and everything above it keeps using the plain symmetric `g` for all *hypothetical remaining* games — that's what `implied_game_win_rate` was solved against, and applying the bonus to future games too would make the model internally inconsistent (the inversion assumed i.i.d. `g` with no serve asymmetry).

### Pre-match probability

```
P0 = logistic(0.6 · ELOdiff/400 + 0.25 · h2h_edge + 0.15 · form_edge)
```

- `ELOdiff` = live match ELO from the broadcast payload (`GameServer.elo - GameServer.other_elo`), not a historical/clustered ELO — the live feed already carries current-session ELO for both players.
- `h2h_edge = (wins_a - wins_b) / (total + 4)` (Laplace-style shrinkage so a 1-0 record doesn't swing as hard as a 20-15 one). If a surface+mod-specific H2H record exists, it's blended in smoothly: `weight = min(specific_total, 4) / 4`, `h2h_edge = (1-weight)·overall_edge + weight·specific_edge`, where **`specific_edge` uses the identical shrinkage formula** (`(specific_wins_a - specific_wins_b) / (specific_total + 4)`) — same `+4` constant as `overall_edge`, just over the surface/mod-filtered subset. Without matching shrinkage a thin specific record (e.g. 2-0) would swing harder than the blend weight intends. No hard on/off threshold either way, so the signal doesn't jump discontinuously as specific-context matches accumulate.
- `form_edge` = difference in each player's recent (last-30-day) win rate, reusing the win-rate computation already in `get_player_details_async` (factored into a small shared helper, not duplicated).
- These weights (0.6/0.25/0.15) and `SERVE_BONUS` are hand-set starting points, not fitted — there's no labeled outcome data to calibrate against yet. Documented as tunable constants in code.

## Caching

`P0`, `g` (implied game win rate), and `s` (implied set win rate) are computed **once per match** and cached in-process. The cache lives on **`StatsService`**, not `ScraperService` — colocated with the existing `_previous_matches` dict, `_get_identity_key()` (which the cache key reuses), and the new `get_h2h_async()` it calls on a miss. `ScraperService` today holds no per-match analytical state (only `_client`/`_polling_task`/`_cache`); `StatsService` is already the match-identity-and-history owner, so a new `_win_prob_cache: dict[tuple, tuple[float, float, float]]` belongs there, exposed via a new orchestration method `StatsService.get_or_compute_pre_match_rates(server: GameServer) -> tuple[float, float, float] | None` returning the cached `(P0, g, s)` (`None` if either ELO is missing/zero). The live recursion itself (`(P0, g, s)` + `LiveMatchState` → final `{p1, p2}` %) is a separate pure function, `win_probability.live_win_probability(g, s, live_state, sets_to_win) -> dict[str, float]`, kept in `win_probability.py` with the rest of the math — `StatsService` only owns the DB-backed cache, not the recursion.

Cache key: the **same identity tuple `_get_identity_key()` already uses** for rename detection — `(creation_time_ms, port, surface_name, nb_set, player_config)` — **not** `match_id` (which hashes in `match_name`, and would silently orphan the cache the moment a placeholder name like "Waiting" resolves to a real one, causing a visible jump/reset in the displayed %).

Every poll tick, for a cached match, only the cheap forward recursion re-runs (`_race_to_win_prob` → `game_to_set_prob` → `set_to_match_prob`, using the cached `g`/`s` and the freshly parsed `LiveMatchState`) — no DB access on the hot path after the first tick for that match.

**Concurrent new matches within one tick.** If several matches start in the same poll tick, each needs one cache-miss round-trip (`get_h2h_async` + form lookups). These run concurrently via `asyncio.gather` across that tick's new match identities, not sequentially — otherwise a burst of simultaneous new matches would serialize their DB latency and delay that tick's broadcast for every connected client.

## Architecture

Confirmed against the actual broadcast code (`live_scores.py`'s WS handler does `websocket.send_text(current_data.model_dump_json())` — it serializes the `GameServerList` pydantic model directly, no wrapping layer), which fixes exactly where each new field lives:

- **New** `backend/app/services/score_parser.py` — `parse_live_state()`, run for every live `GameServer` regardless of match type.
- **New** `backend/app/services/win_probability.py` — `_race_to_win_prob`, `game_to_set_prob`, `set_to_match_prob`, the inversions, serve-bonus, and `pre_match_probability()`.
- **`GameServer` (`backend/app/models/game_server.py`) gets two new fields, of two different kinds:**
  - `live_state` as a new `@computed_field @property`, exactly like the existing `mode_display`/`sets_display`/`surface_display`/`player_names`/`match_id` — it's a pure sync function of `self.score` + `self.game_info.games_per_set`, so it belongs in the same pattern as the others and needs no external wiring to appear in `model_dump_json()`.
  - `win_probability: dict[str, float] | None = Field(default=None, ...)` as a genuine **stored** field, not computed — it needs an async DB-backed cache lookup on a miss, which a `computed_field` property cannot do (must be synchronous). Pydantic v2 rejects setting undeclared attributes, so this has to be a declared field, set imperatively after construction, not monkey-patched.
- **New** `StatsService.get_h2h_async(name_a, name_b) -> H2HRecord` — reuses the alias-resolution + `finished_matches` scan pattern from `get_player_details_async`, filtered to matches involving exactly both resolved names, returning overall + per-surface + per-mod win counts. Reuses `_is_real()` and the `elo > 0` guard already used throughout `stats_service.py` — no reinvented bot/placeholder filtering.
- **New** `StatsService.get_or_compute_pre_match_rates()` — the cache orchestration described above; returns `(P0, g, s)`, not the final %.
- **New** `win_probability.live_win_probability(g, s, live_state, sets_to_win) -> dict[str, float]` — the pure function combining a cached `(g, s)` with the current tick's `live_state` into the final `{p1, p2}` %; called from `ScraperService` after the cache lookup.
- **New Alembic migration**: `finished_matches` gains `surface: str | None` and `mod: str | None` columns. `_try_finish_match` stamps them from `server.surface_display` and the existing `_detect_mod(server)` — both already computed there, just not persisted today.
- **Modify** `ScraperService.fetch_servers()` — concrete insertion point: between `servers = list(parse_server_data(raw_data))` (currently line 143) and `result = GameServerList(servers=servers, ...)` (currently line 156), loop over `servers`; for each singles server whose names pass `_is_real()` and both ELOs are `> 0`, `await`-call `stats_service.get_or_compute_pre_match_rates(server)` for the cached `(P0, g, s)`, then `server.win_probability = win_probability.live_win_probability(g, s, server.live_state, sets_to_win)`. `live_state` itself needs no separate wiring — it's already present via the computed_field the moment `GameServer` is constructed.
- **Free side-benefit**: `fetch_servers_filtered()` (backing the REST `GET /api/live-scores`) filters the same cached `GameServer` instances, so both new fields reach that endpoint with zero extra wiring.
- **Modify** `frontend/src/stores/scores.ts` — WS payload type gains `win_probability` and `live_state`.
- **Modify** `MatchCard.vue` — delete the local `scoreDisplay` computed; render `server.live_state.sets` / `.current_points` / `.server` directly (same shape, since `score_parser.py` mirrors the frontend's existing display grouping). Add a thin split % bar near the score grid, driven by `server.win_probability`; hidden when `null`.

## Data flow

```
scraper poll (60s), ScraperService.fetch_servers():
  servers = parse_server_data(raw_data)                          # each GameServer.live_state is a computed_field — free

  for server in servers where singles(server) and _is_real(p1) and _is_real(p2)
                          and server.elo > 0 and server.other_elo > 0:
      (P0, g, s) = await stats_service.get_or_compute_pre_match_rates(server)  # cache hit after first tick; identity
                                                                                 # key = _get_identity_key(server), reused;
                                                                                 # concurrent new matches in one tick via asyncio.gather
      server.win_probability = win_probability.live_win_probability(g, s, server.live_state, sets_to_win)
      # is_tiebreak → point_to_tiebreak_prob on real point score; else the game_to_set_prob coin-flip stand-in for *future* tiebreaks

  result = GameServerList(servers=servers, ...)   # win_probability set on every eligible server; live_state always present
→ WebSocket send_text(result.model_dump_json()) → scores.ts store → MatchCard.vue
    → grid always rendered from live_state (computed_field, present on every server)
    → % bar rendered from win_probability, hidden if null
```

## Error handling

- `parse_live_state` can't split the score string → `live_state = None`; `MatchCard.vue` falls back to showing the raw `server.score` text (today's worst case for an unparseable string, unchanged).
- Doubles, bot names, missing/zero ELO on either side → `win_probability = null`, bar hidden, `live_state` still populated and grid still renders.
- No prior H2H meetings → `h2h_edge = 0`, `P0` leans on ELO + form only.
- `get_h2h_async` / form lookup throws (DB error) on the first tick for a match → log and cache `P0` from ELO alone (`h2h_edge = form_edge = 0`); retried next time the match identity is seen fresh (i.e., not retried mid-match — acceptable, matches the "compute once" design).
- Match identity persists across a name resolving from a placeholder (e.g. "Waiting" → real name) because the cache key excludes `match_name` — no discontinuity in the displayed %.

## Testing

Backend (pytest, matching existing `backend/tests/` style):

- `score_parser.py`: table-driven over real score strings — mid-set, deuce (`"40:40"`), advantage (`"40:Ad"` / `"Ad:40"`), tiebreak-shaped point segments (`is_tiebreak=True`, `current_points_numeric` as raw ints), serving marker on either side, unparseable input → `None`.
- `win_probability.py`:
  - `g = 0.5` (equivalently `p = 0.5`) → every level (`_race_to_win_prob` at `target=4` and `target=7`, `game_to_set_prob`, `set_to_match_prob`) returns exactly `0.5` by symmetry.
  - Both inversion round-trips: `implied_game_win_rate(game_to_set_prob(g, 0, 0, games_per_set))` ≈ `g`, **and** `implied_set_win_rate(set_to_match_prob(s, 0, 0, sets_to_win), sets_to_win)` ≈ `s`, both within tolerance.
  - Monotonicity property test: holding `P0` fixed, win probability strictly increases as the leader wins additional points/games/sets, strictly decreases as they lose them.
  - `games_per_set` read from the payload, not hardcoded — a match configured for a non-default value produces a different terminal case than the default.
  - Live tiebreak uses `point_to_tiebreak_prob` on the real point score; a *hypothetical* future tiebreak reached while chaining from an earlier game/set score uses the `game_to_set_prob` coin-flip stand-in — test both paths are reachable and don't cross-apply.
- `StatsService.get_h2h_async`: mocked rows in the `test_player_clusters.py` `_m()` style (no DB) — alias resolution, surface/mod blend weighting at 0/1/2/4+ specific meetings (checking the smooth ramp, not a threshold snap).
- Cache identity: a match whose `match_name` changes mid-poll-sequence (placeholder → real name) keeps the same cached `(P0, g, s)` — mirrors the existing rename-detection test pattern.

Frontend: no new test framework (repo has none today, consistent with the prior spec's decision). Verify in-browser: singles bar renders and updates across a poll tick, doubles/bot cards show no bar but still render the score grid, a blowout score (e.g. 5-2 in a decider) visibly swings the % more than a close early-set score.

## Success criteria

- Singles live match cards show a live win% bar that updates every poll tick with no additional frontend network calls.
- % swings correctly reflect match-state severity (a near-finished decider swings much harder than an early close game) — the whole reason the probability-tree approach was chosen over a flat heuristic bonus.
- Doubles, bot, and unrated-ELO matches show no %, but their score grid still renders — via the same shared parser, not a second implementation.
- H2H and recent-form DB lookups happen once per match (on first sight), never on every poll tick.
- `finished_matches.surface` / `.mod` populate going forward from data already computed in `_try_finish_match` today but not persisted.
- No score-parsing logic duplicated between backend and frontend after this change — `MatchCard.vue`'s local `scoreDisplay` computed is deleted, not left as a second path.
