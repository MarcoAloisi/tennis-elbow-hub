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
- Modeling serve/return skill splits — TE4's feed has no serve stats. A single derived per-point win rate is used, with a flat serve-bonus applied only to the currently in-progress game (see Math model, point 3).
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
    sets: list[tuple[str, str]]              # raw display strings, e.g. [("6","3"), ("4","6"), ("1","1")]
    current_points: tuple[str, str] | None    # raw display strings, e.g. ("00", "40"), ("40", "Ad"); None if no current game segment
    server: int | None                        # 1, 2, or None if the `•` marker is missing/ambiguous
    is_tiebreak: bool                         # current_points don't match {0,15,30,40,Ad,A} on either side
    games_per_set: int                        # from GameInfo.games_per_set; 6 if the field is 0 (TE4's "unset" value)

def parse_live_state(score: str, games_per_set: int) -> LiveMatchState | None:
    """Returns None if `score` doesn't split on ' -- ' or has no set segments — caller falls back gracefully."""
```

`is_tiebreak` detection is a heuristic (point tokens outside the normal `{0,15,30,40,Ad,A}` set imply raw tiebreak point counts) — verify against real captured TE4 score strings during implementation; if it doesn't hold, `is_tiebreak` defaults `False` and the set-recursion's tiebreak terminal case (below) simply won't trigger, degrading gracefully to "no live adjustment past 6-6" rather than crashing.

This struct is computed for **every** live match, singles and doubles — `MatchCard.vue` drops its own `scoreDisplay` parsing entirely and renders `server.live_state` instead. One implementation, not two.

## Probability model

New `backend/app/services/win_probability.py`. Pure functions, no DB access except `pre_match_probability`'s inputs (fetched once and cached — see Caching).

### Point → game → set → match recursion

- `point_to_game_prob(p: float, pts_a: int, pts_b: int) -> float` — probability the player with per-point win rate `p` wins the game from point score `(pts_a, pts_b)` (0-3 index, or deuce/ad states beyond). Deuce has a closed form (`p² / (p² + (1-p)²)`); everything before deuce is a small recursive/DP table over the 5×5 state grid — this is *not* a single closed-form equation end to end, described that way loosely earlier in discussion; it's a memoized recursion with a closed-form deuce base case.
- `game_to_set_prob(g: float, games_a: int, games_b: int, games_per_set: int) -> float` — probability of winning the set from game score `(games_a, games_b)`, treating each remaining game as i.i.d. Bernoulli(`g`). **Explicit terminal case at `games_per_set`-all**: resolves via a single Bernoulli(`g`) trial standing in for the tiebreak (not an unbounded ad-set recursion — TE4 caps at a breaker, the recursion must too).
- `set_to_match_prob(s: float, sets_a: int, sets_b: int, sets_to_win: int) -> float` — probability of winning the match from set score, treating each remaining set as i.i.d. Bernoulli(`s`). `sets_to_win` comes from the **existing** `_detect_format()` mapping in `stats_service.py` (`nb_set` → bo1/bo3/bo5 → sets-to-win 1/2/3) — imported, not reimplemented.
- `implied_game_win_rate(s: float) -> float` / `implied_set_win_rate(p0: float, sets_to_win: int) -> float` — binary-search inverses of the above (both are monotonic and continuous in their rate parameter, so the inversion is well-defined). Computed **once per match**, cached alongside `P0` (see Caching) — not re-solved every poll tick.

### Serve bonus — current game only

A fixed constant (`SERVE_BONUS = 0.08`, heuristic, commented as tunable) is added to the server's per-point rate and subtracted from the returner's, but **only when computing `point_to_game_prob` for the live, in-progress game**. `game_to_set_prob` and everything above it keeps using the plain symmetric `g` for all *hypothetical remaining* games — that's what `implied_game_win_rate` was solved against, and applying the bonus to future games too would make the model internally inconsistent (the inversion assumed i.i.d. `g` with no serve asymmetry).

### Pre-match probability

```
P0 = logistic(0.6 · ELOdiff/400 + 0.25 · h2h_edge + 0.15 · form_edge)
```

- `ELOdiff` = live match ELO from the broadcast payload (`GameServer.elo - GameServer.other_elo`), not a historical/clustered ELO — the live feed already carries current-session ELO for both players.
- `h2h_edge = (wins_a - wins_b) / (total + 4)` (Laplace-style shrinkage so a 1-0 record doesn't swing as hard as a 20-15 one). If a surface+mod-specific H2H record exists, it's blended in smoothly: `weight = min(specific_total, 4) / 4`, `h2h_edge = (1-weight)·overall_edge + weight·specific_edge` — no hard on/off threshold, so the signal doesn't jump discontinuously as specific-context matches accumulate.
- `form_edge` = difference in each player's recent (last-30-day) win rate, reusing the win-rate computation already in `get_player_details_async` (factored into a small shared helper, not duplicated).
- These weights (0.6/0.25/0.15) and `SERVE_BONUS` are hand-set starting points, not fitted — there's no labeled outcome data to calibrate against yet. Documented as tunable constants in code.

## Caching

`P0`, `g` (implied game win rate), and `s` (implied set win rate) are computed **once per match** and cached in-process, alongside the existing `_previous_matches` state in `ScraperService` — not a new stateful class.

Cache key: the **same identity tuple `_get_identity_key()` already uses** in `stats_service.py` for rename detection — `(creation_time_ms, port, surface_name, nb_set, player_config)` — **not** `match_id` (which hashes in `match_name`, and would silently orphan the cache the moment a placeholder name like "Waiting" resolves to a real one, causing a visible jump/reset in the displayed %).

Every poll tick, for a cached match, only the cheap forward recursion re-runs (`point_to_game_prob` → `game_to_set_prob` → `set_to_match_prob`, using the cached `g`/`s` and the freshly parsed `LiveMatchState`) — no DB access on the hot path after the first tick for that match.

## Architecture

- **New** `backend/app/services/score_parser.py` — `parse_live_state()`, run for every live `GameServer` regardless of match type.
- **New** `backend/app/services/win_probability.py` — the recursion, inversion, serve-bonus, and `pre_match_probability()` functions above.
- **New** `StatsService.get_h2h_async(name_a, name_b) -> H2HRecord` — reuses the alias-resolution + `finished_matches` scan pattern from `get_player_details_async`, filtered to matches involving exactly both resolved names, returning overall + per-surface + per-mod win counts. Reuses `_is_real()` and the `elo > 0` guard already used throughout `stats_service.py` — no reinvented bot/placeholder filtering.
- **New Alembic migration**: `finished_matches` gains `surface: str | None` and `mod: str | None` columns. `_try_finish_match` stamps them from `server.surface_display` and the existing `_detect_mod(server)` — both already computed there, just not persisted today.
- **Modify** `ScraperService`'s poll loop: for each live server, call `parse_live_state()` (always); if singles + both names pass `_is_real()` + both ELOs `> 0`, get-or-compute the cached `(P0, g, s)` for that match identity (first tick: awaits `get_h2h_async` + form lookups; later ticks: cache hit, no DB), then run the live recursion and attach `win_probability: {p1, p2} | null` and `live_state` to the broadcast payload alongside the existing `GameServer` fields.
- **Modify** `GameServer`/broadcast schema (`backend/app/models/game_server.py` or the WS payload assembly, whichever currently shapes the broadcast) to carry the two new optional fields.
- **Modify** `frontend/src/stores/scores.ts` — WS payload type gains `win_probability` and `live_state`.
- **Modify** `MatchCard.vue` — delete the local `scoreDisplay` computed; render `server.live_state.sets` / `.current_points` / `.server` directly (same shape, since `score_parser.py` mirrors the frontend's existing display grouping). Add a thin split % bar near the score grid, driven by `server.win_probability`; hidden when `null`.

## Data flow

```
scraper poll (60s) → for each live GameServer:
    live_state = parse_live_state(server.score, server.game_info.games_per_set)   [always]

    if singles(server) and _is_real(p1) and _is_real(p2) and server.elo > 0 and server.other_elo > 0:
        identity = _get_identity_key(server)
        (P0, g, s) = cache.get(identity) or compute_and_cache(identity)            [DB hit only on first tick per match]
        win_probability = live_recursion(g, s, live_state, sets_to_win)
    else:
        win_probability = null

    attach {live_state, win_probability} to broadcast payload
→ WebSocket → scores.ts store → MatchCard.vue
    → grid always rendered from live_state
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

- `score_parser.py`: table-driven over real score strings — mid-set, deuce (`"40:40"`), advantage (`"40:Ad"` / `"Ad:40"`), tiebreak-shaped point segments, serving marker on either side, unparseable input → `None`.
- `win_probability.py`:
  - `g = 0.5` → every level (`point_to_game_prob`, `game_to_set_prob`, `set_to_match_prob`) returns exactly `0.5` by symmetry.
  - Inversion round-trip: `implied_game_win_rate(game_to_set_prob(g, 0, 0, games_per_set))` ≈ `g` within tolerance.
  - Monotonicity property test: holding `P0` fixed, win probability strictly increases as the leader wins additional points/games/sets, strictly decreases as they lose them.
  - `games_per_set` read from the payload, not hardcoded — a match configured for a non-default value produces a different terminal case than the default.
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
