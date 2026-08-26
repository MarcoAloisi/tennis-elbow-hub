# Live Win-Probability % Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live-updating win% per player to singles Live Scores match cards, computed server-side from ELO + head-to-head record + recent form + the current in-match score, broadcast with the existing WebSocket payload.

**Architecture:** Two new pure-math backend modules (`score_parser.py` parses the raw score string into structured numeric state; `win_probability.py` runs a point→game→set→match probability recursion). `StatsService` gains a DB-backed, per-match cache for the slow-changing pre-match inputs (ELO/H2H/form), computed once and reused every poll tick. `GameServer` gets a `live_state` computed field (cheap, every tick) and a `win_probability` stored field (set once per tick in the scraper's fetch loop). Frontend drops its own score-parsing logic in favor of the server-provided structured state.

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy async / Pydantic v2 / pytest (backend); Vue 3 / TypeScript (frontend, no test framework in this repo).

**Spec:** `docs/superpowers/specs/2026-08-26-live-win-probability-design.md`

## Global Constraints

- Singles matches only — doubles never get `win_probability`, but always get `live_state` (score parsing is unconditional).
- `score_parser.py` is the **only** module that touches raw score-string tokens. `win_probability.py` consumes plain integers exclusively.
- The pre-match component (`P0`, `g`, `s`) is computed **once per match** and cached — no DB access after the first tick for a given match.
- Cache key is the existing rename-safe identity tuple (`creation_time_ms, port, surface_name, nb_set, player_config`), never `match_id` (which embeds `match_name` and breaks on a name resolving mid-match).
- `SERVE_BONUS = 0.08` and the blend weights `0.6/0.25/0.15` are hand-set, tunable constants — comment them as such, do not present them as calibrated.
- No new frontend test framework (none exists in this repo today) — frontend verification is manual, in-browser.

---

## Task 1: `score_parser.py` — structured live match state

**Files:**
- Create: `backend/app/services/score_parser.py`
- Test: `backend/tests/test_score_parser.py`

**Interfaces:**
- Produces: `LiveMatchState` (frozen dataclass) and `parse_live_state(score: str, games_per_set: int) -> LiveMatchState | None`, both imported by `win_probability.py` (Tasks 2-6) and `game_server.py` (Task 7).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_score_parser.py
from app.services.score_parser import parse_live_state


def test_unparseable_returns_none():
    assert parse_live_state("", 6) is None
    assert parse_live_state("garbage", 6) is None


def test_no_set_segments_returns_none():
    assert parse_live_state(" -- 00:40", 6) is None


def test_mid_set_score():
    state = parse_live_state("6/3 4/6 1/1 -- 00:40•", 6)
    assert state is not None
    assert state.sets == [("6", "3"), ("4", "6"), ("1", "1")]
    assert state.sets_won == (1, 1)
    assert state.current_set_games == (1, 1)
    assert state.current_points == ("00", "40")
    assert state.current_points_numeric == (0, 3)
    assert state.server == 1
    assert state.is_tiebreak is False
    assert state.games_per_set == 6


def test_server_marker_on_p2_side():
    state = parse_live_state("6/3 -- •40:15", 6)
    assert state.server == 2
    assert state.current_points == ("40", "15")


def test_deuce():
    state = parse_live_state("0/0 -- 40:40", 6)
    assert state.current_points_numeric == (3, 3)


def test_advantage_p1():
    state = parse_live_state("0/0 -- 40:Ad", 6)
    assert state.current_points_numeric == (3, 4)


def test_advantage_p2():
    state = parse_live_state("0/0 -- Ad:40", 6)
    assert state.current_points_numeric == (4, 3)


def test_tiebreak_point_counts_as_raw_ints():
    state = parse_live_state("6/6 -- 3:5•", 6)
    assert state.is_tiebreak is True
    assert state.current_points_numeric == (3, 5)
    assert state.server == 1


def test_no_current_game_segment():
    state = parse_live_state("0/0 -- ", 6)
    assert state.current_points is None
    assert state.current_points_numeric is None


def test_games_per_set_zero_falls_back_to_six():
    state = parse_live_state("6/3 -- 00:40", 0)
    assert state.games_per_set == 6


def test_first_set_win_counted():
    state = parse_live_state("6/3 -- 00:40", 6)
    assert state.sets_won == (1, 0)
    assert state.current_set_games == (0, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_score_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.score_parser'`

- [ ] **Step 3: Implement `score_parser.py`**

```python
"""Parses TE4's raw live-score string into structured numeric state.

Format: "6/3 4/6 1/1 -- 00:40•" or "6/3 4/6 1/1 -- •00:40"

This is the single owner of score-token interpretation in the backend —
win_probability.py consumes only the plain-integer fields below, never the
raw string, so the token vocabulary (point table, tiebreak detection,
serve-marker position) lives in exactly one place.
"""

from dataclasses import dataclass

_POINT_TABLE = {"0": 0, "00": 0, "15": 1, "30": 2, "40": 3}


@dataclass(frozen=True)
class LiveMatchState:
    sets: list[tuple[str, str]]
    sets_won: tuple[int, int]
    current_set_games: tuple[int, int]
    current_points: tuple[str, str] | None
    current_points_numeric: tuple[int, int] | None
    server: int | None
    is_tiebreak: bool
    games_per_set: int


def _parse_int(raw: str) -> int | None:
    digits = "".join(c for c in raw if c.isdigit())
    return int(digits) if digits else None


def parse_live_state(score: str, games_per_set: int) -> LiveMatchState | None:
    """Returns None if `score` has no set segments — caller falls back gracefully."""
    if not score or " -- " not in score:
        return None

    sets_part, _, current_part = score.partition(" -- ")
    sets: list[tuple[str, str]] = []
    for token in sets_part.strip().split():
        if "/" not in token:
            continue
        p1, p2 = token.split("/", 1)
        sets.append((p1, p2))

    if not sets:
        return None

    effective_games_per_set = games_per_set if games_per_set > 0 else 6

    # Completed sets are all but the last (in-progress) entry. Winner per
    # entry decided by comparing its two game counts.
    sets_won = [0, 0]
    for p1_raw, p2_raw in sets[:-1]:
        p1_n, p2_n = _parse_int(p1_raw), _parse_int(p2_raw)
        if p1_n is None or p2_n is None:
            continue
        if p1_n > p2_n:
            sets_won[0] += 1
        elif p2_n > p1_n:
            sets_won[1] += 1

    last_p1, last_p2 = sets[-1]
    current_set_games = (_parse_int(last_p1) or 0, _parse_int(last_p2) or 0)

    server: int | None = None
    current_raw = current_part.strip()
    if current_raw.startswith("•"):
        server = 1
        current_raw = current_raw[1:]
    elif current_raw.endswith("•"):
        server = 2
        current_raw = current_raw[:-1]

    current_points: tuple[str, str] | None = None
    current_points_numeric: tuple[int, int] | None = None
    is_tiebreak = False

    if ":" in current_raw:
        raw_p1, raw_p2 = current_raw.split(":", 1)
        current_points = (raw_p1, raw_p2)
        if raw_p1 in _POINT_TABLE and raw_p2 in _POINT_TABLE:
            current_points_numeric = (_POINT_TABLE[raw_p1], _POINT_TABLE[raw_p2])
        elif raw_p1 in ("Ad", "A"):
            current_points_numeric = (4, 3)
        elif raw_p2 in ("Ad", "A"):
            current_points_numeric = (3, 4)
        else:
            # Tokens outside the normal game vocabulary imply raw tiebreak
            # point counts.
            n1, n2 = _parse_int(raw_p1), _parse_int(raw_p2)
            if n1 is not None and n2 is not None:
                is_tiebreak = True
                current_points_numeric = (n1, n2)

    return LiveMatchState(
        sets=sets,
        sets_won=(sets_won[0], sets_won[1]),
        current_set_games=current_set_games,
        current_points=current_points,
        current_points_numeric=current_points_numeric,
        server=server,
        is_tiebreak=is_tiebreak,
        games_per_set=effective_games_per_set,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_score_parser.py -v`
Expected: PASS (all 11 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/score_parser.py backend/tests/test_score_parser.py
git commit -m "feat: parse live TE4 score string into structured numeric state"
```

---

## Task 2: `win_probability.py` — point-race recursion

**Files:**
- Create: `backend/app/services/win_probability.py`
- Test: `backend/tests/test_win_probability.py`

**Interfaces:**
- Consumes: nothing (pure math).
- Produces: `_race_to_win_prob(p, target, a, b) -> float`, `point_to_game_prob(p, a, b) -> float`, `point_to_tiebreak_prob(p, a, b) -> float` — used by Task 3 and Task 5.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_win_probability.py
from app.services.win_probability import (
    point_to_game_prob,
    point_to_tiebreak_prob,
)


def test_symmetric_point_rate_is_fifty_fifty():
    assert point_to_game_prob(0.5, 0, 0) == 0.5
    assert point_to_tiebreak_prob(0.5, 0, 0) == 0.5


def test_game_win_from_match_point():
    # 40-0 (3-0): one more point at p=0.5 doesn't guarantee it, but a
    # dominant p should push the win prob close to 1.
    assert point_to_game_prob(0.9, 3, 0) > 0.9


def test_game_deuce_is_symmetric_closed_form():
    # At exactly deuce (3-3) with p=0.5, win prob is 0.5 regardless of path.
    assert abs(point_to_game_prob(0.5, 3, 3) - 0.5) < 1e-9


def test_game_advantage_beats_deuce():
    # Advantage-in (4-3) is a strictly better position than deuce (3-3).
    p = 0.6
    assert point_to_game_prob(p, 4, 3) > point_to_game_prob(p, 3, 3)


def test_game_recursion_terminates_from_advantage_state():
    # Regression: a naive recursion that only special-cases the exact
    # (target-1, target-1) tied state recurses forever from (4,3) -> (4,4)
    # -> (5,5) -> ... because those re-tied states are never (3,3) again.
    # This must resolve instantly and be a valid probability.
    result = point_to_game_prob(0.5, 4, 3)
    assert 0.0 <= result <= 1.0


def test_tiebreak_win_from_match_point():
    assert point_to_tiebreak_prob(0.9, 6, 2) > 0.99


def test_game_and_tiebreak_share_the_same_recursion_shape():
    # Different targets (4 vs 7), same win-by-2 structure.
    assert point_to_game_prob(0.7, 0, 0) != point_to_tiebreak_prob(0.7, 0, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.win_probability'`

- [ ] **Step 3: Implement the recursion**

```python
# backend/app/services/win_probability.py
"""Live tennis win-probability math: point -> game -> set -> match.

Pure functions, no DB access. `pre_match_probability`'s inputs (ELO, H2H,
recent form) are fetched and cached once per match by StatsService — see
`get_or_compute_pre_match_rates` there. Everything in this module consumes
plain integers only; score_parser.py is the sole owner of raw score-token
interpretation.
"""

import math


def _race_to_win_prob(p: float, target: int, a: int, b: int) -> float:
    """Probability the player with per-point win rate `p` wins a race to
    `target` points (win by 2) from score (a, b).

    The tied-at-the-wire closed form applies at ANY tied score at or beyond
    target-1, not only the literal (target-1, target-1) — a state like
    (target, target-1) is reachable directly (e.g. "advantage" is mapped to
    one point past deuce by score_parser), and from there the general
    recursive step can revisit tied states again at (target+1, target+1),
    (target+2, target+2), etc. Those are deuce-equivalent by the same
    geometric-series argument, so `a == b and a >= target - 1` must be the
    guard, not `a == b == target - 1` — the narrower check lets the
    recursion re-enter itself indefinitely from an already-advanced start.
    """
    memo: dict[tuple[int, int], float] = {}

    def _rec(a: int, b: int) -> float:
        key = (a, b)
        if key in memo:
            return memo[key]
        if a >= target and a - b >= 2:
            result = 1.0
        elif b >= target and b - a >= 2:
            result = 0.0
        elif a == b and a >= target - 1:
            result = (p * p) / (p * p + (1 - p) * (1 - p))
        else:
            result = p * _rec(a + 1, b) + (1 - p) * _rec(a, b + 1)
        memo[key] = result
        return result

    return _rec(a, b)


def point_to_game_prob(p: float, a: int, b: int) -> float:
    return _race_to_win_prob(p, 4, a, b)


def point_to_tiebreak_prob(p: float, a: int, b: int) -> float:
    return _race_to_win_prob(p, 7, a, b)


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/win_probability.py backend/tests/test_win_probability.py
git commit -m "feat: add point-race win-probability recursion (game/tiebreak)"
```

---

## Task 3: `win_probability.py` — game→set and set→match recursion

**Files:**
- Modify: `backend/app/services/win_probability.py`
- Modify: `backend/tests/test_win_probability.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `game_to_set_prob(g, games_a, games_b, games_per_set) -> float`, `set_to_match_prob(s, sets_a, sets_b, sets_to_win) -> float` — used by Task 4 (inversions) and Task 5 (live orchestration).

- [ ] **Step 1: Write the failing tests**

```python
# append to backend/tests/test_win_probability.py
from app.services.win_probability import game_to_set_prob, set_to_match_prob


def test_symmetric_game_rate_set_is_fifty_fifty():
    assert game_to_set_prob(0.5, 0, 0, 6) == 0.5


def test_set_win_from_five_love():
    assert game_to_set_prob(0.5, 5, 0, 6) > 0.95


def test_set_terminal_case_at_games_all_uses_g_as_tiebreak_stand_in():
    # At 6-6, the set is decided by one Bernoulli(g) "trial" — a stand-in
    # for the hypothetical, not-yet-reached tiebreak.
    assert game_to_set_prob(0.7, 6, 6, 6) == 0.7


def test_set_does_not_go_past_games_per_set_plus_one():
    # 7-5 is a legal, terminal, no-tiebreak set win — must not recurse
    # toward 8-6 or beyond.
    p = game_to_set_prob(0.5, 7, 5, 6)
    assert p == 1.0


def test_non_default_games_per_set_changes_terminal_case():
    # A match configured for a shorter set (e.g. games_per_set=4) must use
    # that value, not a hardcoded 6. g=0.5 is deliberately NOT used here: at
    # a symmetric point-win-rate, (3,3) resolves to exactly 0.5 whether it's
    # the games_per_set=4 terminal case OR a mid-recursion tied state in a
    # games_per_set=6 set (by the same complementary-symmetry argument as
    # the deuce closed form) — the two would coincidentally match and this
    # test would not actually be checking what its name claims.
    short_set = game_to_set_prob(0.65, 3, 3, 4)
    long_set = game_to_set_prob(0.65, 3, 3, 6)
    assert short_set != long_set


def test_symmetric_set_rate_match_is_fifty_fifty():
    assert set_to_match_prob(0.5, 0, 0, 2) == 0.5


def test_match_win_from_two_sets_up_in_best_of_three():
    assert set_to_match_prob(0.5, 2, 0, 2) == 1.0


def test_best_of_five_needs_three_sets():
    assert set_to_match_prob(0.5, 2, 0, 3) < 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: FAIL with `ImportError: cannot import name 'game_to_set_prob'`

- [ ] **Step 3: Implement**

```python
# append to backend/app/services/win_probability.py

def game_to_set_prob(g: float, games_a: int, games_b: int, games_per_set: int) -> float:
    """Probability of winning the set from game score (games_a, games_b),
    treating each remaining game as i.i.d. Bernoulli(g).

    Terminal case at games_per_set-all resolves via a single Bernoulli(g)
    trial standing in for a hypothetical, not-yet-reached tiebreak — TE4
    caps a set at a breaker, so this recursion must terminate there rather
    than run an unbounded ad-set. This approximation only applies to a
    tiebreak that might happen later in the chain; a tiebreak the match is
    actually inside right now uses point_to_tiebreak_prob on the real point
    score instead (see live_win_probability in Task 5).
    """
    memo: dict[tuple[int, int], float] = {}

    def _rec(a: int, b: int) -> float:
        key = (a, b)
        if key in memo:
            return memo[key]
        if a >= games_per_set and a - b >= 2:
            result = 1.0
        elif b >= games_per_set and b - a >= 2:
            result = 0.0
        elif a == games_per_set and b == games_per_set:
            result = g
        else:
            result = g * _rec(a + 1, b) + (1 - g) * _rec(a, b + 1)
        memo[key] = result
        return result

    return _rec(games_a, games_b)


def set_to_match_prob(s: float, sets_a: int, sets_b: int, sets_to_win: int) -> float:
    """Probability of winning the match from set score, treating each
    remaining set as i.i.d. Bernoulli(s). No win-by-2 concept at this level
    — first to `sets_to_win` wins outright.
    """
    memo: dict[tuple[int, int], float] = {}

    def _rec(a: int, b: int) -> float:
        key = (a, b)
        if key in memo:
            return memo[key]
        if a >= sets_to_win:
            result = 1.0
        elif b >= sets_to_win:
            result = 0.0
        else:
            result = s * _rec(a + 1, b) + (1 - s) * _rec(a, b + 1)
        memo[key] = result
        return result

    return _rec(sets_a, sets_b)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: PASS (all 15 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/win_probability.py backend/tests/test_win_probability.py
git commit -m "feat: add game-to-set and set-to-match win-probability recursion"
```

---

## Task 4: `win_probability.py` — inversions (implied game/set win rates)

**Files:**
- Modify: `backend/app/services/win_probability.py`
- Modify: `backend/tests/test_win_probability.py`

**Interfaces:**
- Consumes: `game_to_set_prob`, `set_to_match_prob` (Task 3).
- Produces: `implied_game_win_rate(s, games_per_set) -> float`, `implied_set_win_rate(p0, sets_to_win) -> float` — used by Task 6 (`StatsService.get_or_compute_pre_match_rates`, Task 12).

- [ ] **Step 1: Write the failing tests**

```python
# append to backend/tests/test_win_probability.py
from app.services.win_probability import implied_game_win_rate, implied_set_win_rate


def test_implied_game_win_rate_round_trip():
    for g in (0.3, 0.5, 0.65, 0.8):
        s = game_to_set_prob(g, 0, 0, 6)
        assert abs(implied_game_win_rate(s, 6) - g) < 1e-4


def test_implied_set_win_rate_round_trip():
    for s in (0.3, 0.5, 0.65, 0.8):
        p0 = set_to_match_prob(s, 0, 0, 2)
        assert abs(implied_set_win_rate(p0, 2) - s) < 1e-4


def test_implied_game_win_rate_symmetric_at_half():
    assert abs(implied_game_win_rate(0.5, 6) - 0.5) < 1e-4


def test_implied_set_win_rate_symmetric_at_half():
    assert abs(implied_set_win_rate(0.5, 2) - 0.5) < 1e-4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: FAIL with `ImportError: cannot import name 'implied_game_win_rate'`

- [ ] **Step 3: Implement**

```python
# append to backend/app/services/win_probability.py

def implied_game_win_rate(s: float, games_per_set: int) -> float:
    """Binary-search inverse of game_to_set_prob(g, 0, 0, games_per_set) — g
    is monotonic and continuous in game_to_set_prob's output, so this is
    well-defined."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if game_to_set_prob(mid, 0, 0, games_per_set) < s:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def implied_set_win_rate(p0: float, sets_to_win: int) -> float:
    """Binary-search inverse of set_to_match_prob(s, 0, 0, sets_to_win)."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if set_to_match_prob(mid, 0, 0, sets_to_win) < p0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: PASS (all 19 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/win_probability.py backend/tests/test_win_probability.py
git commit -m "feat: add binary-search inversions for implied game/set win rates"
```

---

## Task 5: `win_probability.py` — live orchestration (`live_win_probability`)

**Files:**
- Modify: `backend/app/services/win_probability.py`
- Modify: `backend/tests/test_win_probability.py`

**Interfaces:**
- Consumes: `LiveMatchState` (Task 1), `point_to_game_prob`/`point_to_tiebreak_prob` (Task 2), `game_to_set_prob`/`set_to_match_prob` (Task 3).
- Produces: `live_win_probability(g: float, s: float, live_state: LiveMatchState, sets_to_win: int) -> dict[str, float]` — the function `ScraperService.fetch_servers()` calls every tick (Task 13).

- [ ] **Step 1: Write the failing tests**

```python
# append to backend/tests/test_win_probability.py
from app.services.score_parser import LiveMatchState
from app.services.win_probability import live_win_probability


def _state(**overrides) -> LiveMatchState:
    base = dict(
        sets=[("0", "0")],
        sets_won=(0, 0),
        current_set_games=(0, 0),
        current_points=("00", "00"),
        current_points_numeric=(0, 0),
        server=1,
        is_tiebreak=False,
        games_per_set=6,
    )
    base.update(overrides)
    return LiveMatchState(**base)


def test_symmetric_rates_start_at_fifty_fifty():
    result = live_win_probability(0.5, 0.5, _state(server=None), sets_to_win=2)
    assert abs(result["p1"] - 0.5) < 1e-3
    assert abs(result["p2"] - 0.5) < 1e-3
    assert abs(result["p1"] + result["p2"] - 1.0) < 1e-9


def test_serve_bonus_favors_the_current_server():
    with_serve = live_win_probability(0.5, 0.5, _state(server=1), sets_to_win=2)
    no_serve = live_win_probability(0.5, 0.5, _state(server=None), sets_to_win=2)
    assert with_serve["p1"] > no_serve["p1"]


def test_leading_two_sets_to_love_is_near_certain():
    result = live_win_probability(
        0.55, 0.6, _state(sets_won=(2, 0), current_set_games=(0, 0), server=None),
        sets_to_win=2,
    )
    assert result["p1"] > 0.99


def test_blowout_decider_lead_swings_harder_than_early_close_game():
    blowout = live_win_probability(
        0.5, 0.5,
        _state(sets_won=(1, 1), current_set_games=(5, 2), server=1,
               current_points=("40", "15"), current_points_numeric=(3, 1)),
        sets_to_win=2,
    )
    close_early = live_win_probability(
        0.5, 0.5,
        _state(sets_won=(0, 0), current_set_games=(1, 0), server=1,
               current_points=("40", "15"), current_points_numeric=(3, 1)),
        sets_to_win=2,
    )
    assert (blowout["p1"] - 0.5) > (close_early["p1"] - 0.5)


def test_live_tiebreak_uses_real_point_score_not_coin_flip():
    near_tiebreak_win = live_win_probability(
        0.5, 0.5,
        _state(sets_won=(0, 0), current_set_games=(6, 6), server=1, is_tiebreak=True,
               current_points=("6", "2"), current_points_numeric=(6, 2)),
        sets_to_win=2,
    )
    assert near_tiebreak_win["p1"] > 0.9


def test_monotonicity_more_points_only_helps():
    behind = live_win_probability(
        0.5, 0.5,
        _state(current_points=("00", "40"), current_points_numeric=(0, 3)),
        sets_to_win=2,
    )
    ahead = live_win_probability(
        0.5, 0.5,
        _state(current_points=("40", "00"), current_points_numeric=(3, 0)),
        sets_to_win=2,
    )
    assert ahead["p1"] > behind["p1"]


def test_probabilities_always_sum_to_one():
    result = live_win_probability(
        0.62, 0.58,
        _state(sets_won=(1, 0), current_set_games=(3, 4), server=2,
               current_points=("30", "40"), current_points_numeric=(2, 3)),
        sets_to_win=2,
    )
    assert abs(result["p1"] + result["p2"] - 1.0) < 1e-9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: FAIL with `ImportError: cannot import name 'live_win_probability'`

- [ ] **Step 3: Implement**

```python
# append to backend/app/services/win_probability.py
from app.services.score_parser import LiveMatchState

SERVE_BONUS = 0.08  # heuristic starting point, not fitted — tune once real outcome data exists


def _serve_adjusted_point_rate(g: float, server: int | None) -> float:
    """Player-1-perspective per-point win rate for the live game/tiebreak,
    boosted if p1 is serving, reduced if p2 is serving. Unadjusted (plain g)
    if the server marker is missing/ambiguous."""
    if server == 1:
        return min(g + SERVE_BONUS, 0.999)
    if server == 2:
        return max(g - SERVE_BONUS, 0.001)
    return g


def _game_to_set_with_current_game(
    game_prob_a: float, g: float, games_a: int, games_b: int, games_per_set: int
) -> float:
    """Threads the live (possibly serve-adjusted) current-game win prob into
    the set recursion; every game beyond the current one reverts to the
    plain symmetric g, matching what implied_game_win_rate was solved
    against."""
    if games_a >= games_per_set or games_b >= games_per_set:
        return game_to_set_prob(g, games_a, games_b, games_per_set)
    win_next = game_to_set_prob(g, games_a + 1, games_b, games_per_set)
    lose_next = game_to_set_prob(g, games_a, games_b + 1, games_per_set)
    return game_prob_a * win_next + (1 - game_prob_a) * lose_next


def _set_to_match_with_current_set(
    set_prob_a: float, s: float, sets_a: int, sets_b: int, sets_to_win: int
) -> float:
    """Same threading as _game_to_set_with_current_game, one level up."""
    if sets_a >= sets_to_win or sets_b >= sets_to_win:
        return set_to_match_prob(s, sets_a, sets_b, sets_to_win)
    win_next = set_to_match_prob(s, sets_a + 1, sets_b, sets_to_win)
    lose_next = set_to_match_prob(s, sets_a, sets_b + 1, sets_to_win)
    return set_prob_a * win_next + (1 - set_prob_a) * lose_next


def live_win_probability(
    g: float, s: float, live_state: LiveMatchState, sets_to_win: int
) -> dict[str, float]:
    """Combines the cached (g, s) with the current tick's live_state into
    the final {p1, p2} win probability. is_tiebreak routes to the real
    race-to-7 point score; otherwise the current game's real point score is
    used. Either way, only the CURRENT game/tiebreak gets the serve-bonus
    adjustment — everything beyond it uses the plain symmetric rate that the
    (g, s) inversion assumed."""
    sets_a, sets_b = live_state.sets_won
    games_a, games_b = live_state.current_set_games

    if live_state.current_points_numeric is not None:
        pts_a, pts_b = live_state.current_points_numeric
        p_adj = _serve_adjusted_point_rate(g, live_state.server)
        if live_state.is_tiebreak:
            game_prob_a = point_to_tiebreak_prob(p_adj, pts_a, pts_b)
        else:
            game_prob_a = point_to_game_prob(p_adj, pts_a, pts_b)
    else:
        game_prob_a = g

    set_prob_a = _game_to_set_with_current_game(
        game_prob_a, g, games_a, games_b, live_state.games_per_set
    )
    match_prob_a = _set_to_match_with_current_set(set_prob_a, s, sets_a, sets_b, sets_to_win)

    p1 = round(match_prob_a, 4)
    return {"p1": p1, "p2": round(1 - p1, 4)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: PASS (all 26 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/win_probability.py backend/tests/test_win_probability.py
git commit -m "feat: add live win-probability orchestration with current-game serve bonus"
```

---

## Task 6: `win_probability.py` — pre-match blend (`H2HRecord`, `pre_match_probability`)

**Files:**
- Modify: `backend/app/services/win_probability.py`
- Modify: `backend/tests/test_win_probability.py`

**Interfaces:**
- Consumes: `logistic` (Task 2).
- Produces: `H2HRecord` (frozen dataclass), `h2h_edge(record) -> float`, `form_edge(form_a, form_b) -> float`, `pre_match_probability(elo_a, elo_b, h2h, form_edge_value) -> float` — used by `StatsService.get_or_compute_pre_match_rates` (Task 12), and `H2HRecord` is the return type of `StatsService.get_h2h_async` (Task 10).

- [ ] **Step 1: Write the failing tests**

```python
# append to backend/tests/test_win_probability.py
from app.services.win_probability import H2HRecord, form_edge, h2h_edge, pre_match_probability


def test_h2h_edge_no_history_is_neutral():
    record = H2HRecord(wins_a=0, wins_b=0, total=0, specific_wins_a=0, specific_wins_b=0, specific_total=0)
    assert h2h_edge(record) == 0.0


def test_h2h_edge_favors_more_wins():
    record = H2HRecord(wins_a=3, wins_b=1, total=4, specific_wins_a=0, specific_wins_b=0, specific_total=0)
    assert h2h_edge(record) > 0


def test_h2h_edge_shrinkage_dampens_small_samples():
    small = H2HRecord(wins_a=1, wins_b=0, total=1, specific_wins_a=0, specific_wins_b=0, specific_total=0)
    large = H2HRecord(wins_a=15, wins_b=0, total=15, specific_wins_a=0, specific_wins_b=0, specific_total=0)
    assert h2h_edge(small) < h2h_edge(large)


def test_h2h_edge_specific_blend_uses_matching_shrinkage():
    # A thin specific record (2-0) blended at weight min(2,4)/4=0.5 should
    # land between the overall and specific shrunk edges, not overshoot
    # because of mismatched shrinkage.
    record = H2HRecord(wins_a=5, wins_b=5, total=10, specific_wins_a=2, specific_wins_b=0, specific_total=2)
    overall = (5 - 5) / (10 + 4)
    specific = (2 - 0) / (2 + 4)
    expected = 0.5 * overall + 0.5 * specific
    assert abs(h2h_edge(record) - expected) < 1e-9


def test_h2h_edge_no_specific_data_ignores_blend():
    record = H2HRecord(wins_a=2, wins_b=1, total=3, specific_wins_a=0, specific_wins_b=0, specific_total=0)
    assert h2h_edge(record) == (2 - 1) / (3 + 4)


def test_form_edge_no_data_is_neutral():
    assert form_edge(None, None) == 0.0
    assert form_edge(0.7, None) == 0.0
    assert form_edge(None, 0.7) == 0.0


def test_form_edge_difference():
    assert abs(form_edge(0.7, 0.4) - 0.3) < 1e-9


def test_pre_match_probability_symmetric_elo_and_no_data_is_half():
    record = H2HRecord(0, 0, 0, 0, 0, 0)
    assert abs(pre_match_probability(1500, 1500, record, 0.0) - 0.5) < 1e-9


def test_pre_match_probability_higher_elo_favored():
    record = H2HRecord(0, 0, 0, 0, 0, 0)
    p = pre_match_probability(1700, 1500, record, 0.0)
    assert p > 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: FAIL with `ImportError: cannot import name 'H2HRecord'`

- [ ] **Step 3: Implement**

```python
# append to backend/app/services/win_probability.py
from dataclasses import dataclass


@dataclass(frozen=True)
class H2HRecord:
    wins_a: int
    wins_b: int
    total: int
    specific_wins_a: int
    specific_wins_b: int
    specific_total: int


def _shrunk_edge(wins_a: int, wins_b: int, total: int) -> float:
    return (wins_a - wins_b) / (total + 4)


def h2h_edge(record: H2HRecord) -> float:
    """Laplace-shrunk H2H edge, blended smoothly with a surface/mod-specific
    edge (identically shrunk) when specific data exists — no hard on/off
    threshold, so the signal doesn't jump as specific matches accumulate."""
    overall = _shrunk_edge(record.wins_a, record.wins_b, record.total)
    if record.specific_total == 0:
        return overall
    specific = _shrunk_edge(record.specific_wins_a, record.specific_wins_b, record.specific_total)
    weight = min(record.specific_total, 4) / 4
    return (1 - weight) * overall + weight * specific


def form_edge(form_a: float | None, form_b: float | None) -> float:
    """Difference in recent (last-30-day) win rate. 0.0 (no signal) if
    either player has no recent matches."""
    if form_a is None or form_b is None:
        return 0.0
    return form_a - form_b


def pre_match_probability(
    elo_a: int, elo_b: int, h2h: H2HRecord, form_edge_value: float
) -> float:
    """P0 = logistic(0.6*ELOdiff/400 + 0.25*h2h_edge + 0.15*form_edge).
    Weights are hand-set starting points, not fitted — no labeled outcome
    data exists yet to calibrate against."""
    elo_term = (elo_a - elo_b) / 400.0
    x = 0.6 * elo_term + 0.25 * h2h_edge(h2h) + 0.15 * form_edge_value
    return logistic(x)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_win_probability.py -v`
Expected: PASS (all 35 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/win_probability.py backend/tests/test_win_probability.py
git commit -m "feat: add pre-match ELO/H2H/form blend for win probability"
```

---

## Task 7: `GameServer` model — `live_state` computed field, `win_probability` stored field

**Files:**
- Modify: `backend/app/models/game_server.py`
- Test: `backend/tests/test_game_server_live_state.py`

**Interfaces:**
- Consumes: `parse_live_state` (Task 1).
- Produces: `GameServer.live_state` (property, always present), `GameServer.win_probability` (settable field, default `None`) — consumed by `ScraperService.fetch_servers()` (Task 13) and serialized to the frontend via `model_dump_json()`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_game_server_live_state.py
from app.services.parser import parse_server_data

# Reuses the exact wire-format sample from conftest.py's sample_server_data
# fixture (GameInfo=0x1B198E41, which decodes to games_per_set=6) rather
# than hand-rolling a new one — GameServer's numeric fields (elo, port,
# GameInfo, ...) are parsed via safe_int_from_hex, i.e. HEX, not decimal,
# so a hand-written "elo=1600"-style token would silently parse as 0x1600
# (5632). Going through the real tokenizer with known-good data sidesteps
# that entirely.
_SAMPLE = (
    '0 E9FD "RBI vs TestPlayer" 1B198E41 96 415 3 "XKT v4.2d" '
    '"6/3 4/6 1/1 -- 00:40•" 393 0 1 "BlueGreenCement" 69760194'
)


def _parse_one(raw: str):
    servers = list(parse_server_data(raw))
    assert len(servers) == 1
    return servers[0]


def test_live_state_is_present_on_every_server():
    server = _parse_one(_SAMPLE)
    assert server.live_state is not None
    assert server.live_state.sets == [("6", "3"), ("4", "6"), ("1", "1")]
    assert server.live_state.server == 1


def test_live_state_uses_games_per_set_from_game_info():
    server = _parse_one(_SAMPLE)
    assert server.game_info.games_per_set == 6
    assert server.live_state.games_per_set == 6


def test_win_probability_defaults_to_none():
    server = _parse_one(_SAMPLE)
    assert server.win_probability is None


def test_win_probability_is_settable_and_serializes():
    server = _parse_one(_SAMPLE)
    server.win_probability = {"p1": 0.62, "p2": 0.38}
    dumped = server.model_dump()
    assert dumped["win_probability"] == {"p1": 0.62, "p2": 0.38}
    assert "live_state" in dumped
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_game_server_live_state.py -v`
Expected: FAIL with `AttributeError: 'GameServer' object has no attribute 'live_state'`

- [ ] **Step 3: Implement**

In `backend/app/models/game_server.py`:

1. Add the import at the top of the file:

```python
from app.services.score_parser import LiveMatchState, parse_live_state
```

2. Add a new stored field on `GameServer`, right after `is_started: bool = Field(...)` (currently line 113):

```python
    win_probability: dict[str, float] | None = Field(
        default=None,
        description="Live win probability {p1, p2} — singles matches only, set by ScraperService after construction",
    )
```

3. Add a new `computed_field` on `GameServer`, right after the `match_id` computed_field block (currently ends at line 138, before `surface_display`):

```python
    @computed_field
    @property
    def live_state(self) -> LiveMatchState | None:
        """Structured sets/games/points/server, parsed once here so both
        the win-probability calc and the frontend consume the same
        structure — no second parsing implementation."""
        return parse_live_state(self.score, self.game_info.games_per_set)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_game_server_live_state.py -v`
Expected: PASS (all 4 tests)

Also run the full existing suite to confirm nothing broke:

Run: `cd backend && pytest tests/test_parser.py tests/test_scraper.py -v`
Expected: PASS (unchanged)

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/game_server.py backend/tests/test_game_server_live_state.py
git commit -m "feat: add live_state computed field and win_probability field to GameServer"
```

---

## Task 8: `finished_matches` gains `surface`/`mod` columns

**Files:**
- Modify: `backend/app/models/finished_match.py`
- Create: `backend/alembic/versions/<generated>_add_surface_mod_to_finished_matches.py`

**Interfaces:**
- Produces: `FinishedMatch.surface: str | None`, `FinishedMatch.mod: str | None` — populated in Task 9, read in Task 10 (`get_h2h_async`'s surface/mod breakdown).

- [ ] **Step 1: Modify the model**

In `backend/app/models/finished_match.py`, add two nullable columns after `score`:

```python
    score: Mapped[str | None] = mapped_column(String, nullable=True)
    surface: Mapped[str | None] = mapped_column(String, nullable=True)
    mod: Mapped[str | None] = mapped_column(String, nullable=True)
    p1_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 2: Generate the migration**

Run:
```bash
cd backend
.venv/Scripts/alembic.exe revision --autogenerate -m "add surface and mod to finished_matches"
```

Expected: a new file under `backend/alembic/versions/` with `down_revision = "867755e0f38f"` (the current head) containing two `op.add_column(...)` calls for `finished_matches.surface` and `finished_matches.mod`, both nullable, no server default.

- [ ] **Step 3: Verify the generated migration**

Read the generated file and confirm it matches this shape (edit if autogenerate produced anything different — e.g. wrong table, wrong nullability):

```python
def upgrade() -> None:
    op.add_column("finished_matches", sa.Column("surface", sa.String(), nullable=True))
    op.add_column("finished_matches", sa.Column("mod", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("finished_matches", "mod")
    op.drop_column("finished_matches", "surface")
```

- [ ] **Step 4: Apply the migration**

Run: `cd backend && .venv/Scripts/alembic.exe upgrade head`
Expected: migration applies cleanly; `.venv/Scripts/alembic.exe current` shows the new revision as head.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/finished_match.py backend/alembic/versions/
git commit -m "feat: add surface and mod columns to finished_matches"
```

---

## Task 9: Stamp `surface`/`mod` on finish; extract reusable match-identity key

**Files:**
- Modify: `backend/app/services/stats_service.py:90-97, 192-200`
- Test: `backend/tests/test_stats_service_identity.py`

**Interfaces:**
- Consumes: `FinishedMatch.surface`/`.mod` (Task 8).
- Produces: module-level `_match_identity_key(server: GameServer) -> tuple` — used by `track_matches` (existing rename detection, unchanged behavior) and by the new win-probability cache (Task 12).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_stats_service_identity.py
from app.models.game_server import GameInfo, GameServer, PlayerConfig, SkillMode, ControlMode
from app.services.stats_service import _match_identity_key


def _make_server(match_name: str, port: int = 1, creation_time_ms: int = 100) -> GameServer:
    """Constructs a GameServer directly, bypassing wire-format parsing —
    this test only cares about the identity fields, not the hex tokenizer,
    and GameServer's numeric wire fields are parsed as hex by the real
    parser (safe_int_from_hex), so hand-written decimal-looking raw strings
    would silently parse wrong. Direct construction sidesteps that."""
    return GameServer(
        ip="0.0.0.0",
        port=port,
        match_name=match_name,
        game_info=GameInfo(
            trial=0, player_config=PlayerConfig.SINGLES, nb_set=2,
            skill_mode=SkillMode.INTERMEDIATE, games_per_set=6,
            control_mode=ControlMode.KEYBOARD, preview=0, tiredness=False,
        ),
        max_ping=96, elo=1500, nb_game=3, tag_line="", score="0/0 -- 0:0",
        other_elo=1500, give_up_rate=0, reputation=0, surface_name="Clay",
        creation_time_ms=creation_time_ms, is_started=True,
    )


def test_identity_key_excludes_match_name():
    """A name resolving mid-match (e.g. 'Waiting' -> real name) must not
    change the identity key — that's what makes the win-probability cache
    (and the existing rename-detection logic) survive it."""
    server_a = _make_server("Waiting vs Bob")
    server_b = _make_server("Alice vs Bob")
    assert _match_identity_key(server_a) == _match_identity_key(server_b)


def test_identity_key_differs_on_port():
    server_a = _make_server("Alice vs Bob", port=1)
    server_b = _make_server("Alice vs Bob", port=2)
    assert _match_identity_key(server_a) != _match_identity_key(server_b)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_stats_service_identity.py -v`
Expected: FAIL with `ImportError: cannot import name '_match_identity_key'`

- [ ] **Step 3: Extract the identity key and stamp surface/mod**

In `backend/app/services/stats_service.py`:

1. Add a module-level function (near the top of the file, after the `logger` assignment, before `class StatsService`):

```python
def _match_identity_key(s: GameServer) -> tuple:
    """Rename-safe match identity — excludes match_name so a placeholder
    name (e.g. "Waiting") resolving to a real one mid-match doesn't change
    the key. Used by both finished-match rename detection and the
    win-probability pre-match-rate cache."""
    return (
        s.creation_time_ms,
        s.port,
        s.surface_name,
        s.game_info.nb_set,
        s.game_info.player_config,
    )
```

2. In `track_matches` (currently lines 90-97, 100, 110), delete the local nested `_get_identity_key` function and its two call sites, replacing them with calls to the new module-level `_match_identity_key`:

```python
        new_matches_by_identity = {
            _match_identity_key(current_matches[mid]): mid
            for mid in new_ids
        }

        finished_count = 0

        for match_id in missing_ids:
            server = self._previous_matches[match_id]

            # 1. RENAME DETECTION
            identity_key = _match_identity_key(server)
```

3. In `_try_finish_match` (currently lines 191-206), compute `mod` once, before constructing `match_record`, and stamp both new columns:

```python
                # 2. Insert into finished_matches (Atomic Guard)
                mod = self._detect_mod(server)
                match_record = FinishedMatch(
                    match_id=server.match_id,
                    date=date_obj,
                    match_name=server.match_name,
                    score=clean_score,
                    winner=deduced_winner,
                    surface=server.surface_display,
                    mod=mod,
                    p1_elo=server.elo,
                    p2_elo=server.other_elo
                )
                session.add(match_record)
                await session.flush() # Check constraints immediately

                # 2. Update Aggregates (Only if insert succeeded)
                fmt = self._detect_format(server)
```

(Note: `mod = self._detect_mod(server)` is now computed once above and reused here instead of being called a second time.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_stats_service_identity.py -v`
Expected: PASS (both tests)

Run the existing stats/rename tests to confirm no regression:

Run: `cd backend && pytest tests/test_player_clusters.py tests/test_scraper.py -v`
Expected: PASS (unchanged)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/stats_service.py backend/tests/test_stats_service_identity.py
git commit -m "refactor: extract reusable match-identity key; stamp surface/mod on finish"
```

---

## Task 10: `StatsService` — shared appearances query + H2H

**Files:**
- Modify: `backend/app/services/stats_service.py`
- Test: `backend/tests/test_h2h.py`

**Interfaces:**
- Consumes: `H2HRecord` (Task 6).
- Produces: `StatsService._h2h_from_rows(name_a, name_b, appearances) -> H2HRecord` (pure, tested without DB), `StatsService._fetch_resolved_appearances_async() -> list[dict]` (one DB round-trip, alias-resolved), `StatsService.get_h2h_async(name_a, name_b) -> H2HRecord` (public wrapper: fetch + `_h2h_from_rows`) — `get_h2h_async` used standalone if needed later; the win-probability cache path (Task 12) calls `_fetch_resolved_appearances_async` once and reuses the same list for both H2H and form, avoiding a second round-trip.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_h2h.py
from datetime import date

from app.services.stats_service import _h2h_from_rows


def _appearance(name, opponent, result, surface="Clay", mod="vanilla", day="2026-08-01"):
    return {
        "name": name,
        "opponent": opponent,
        "result": result,
        "surface": surface,
        "mod": mod,
        "date": date.fromisoformat(day),
    }


def test_no_history_is_empty_record():
    record = _h2h_from_rows("Alice", "Bob", [])
    assert record.total == 0
    assert record.wins_a == 0
    assert record.wins_b == 0
    assert record.specific_total == 0


def test_counts_wins_from_both_directions_of_the_same_match():
    appearances = [
        _appearance("Alice", "Bob", "W"),
        _appearance("Bob", "Alice", "L"),
    ]
    record = _h2h_from_rows("Alice", "Bob", appearances)
    assert record.wins_a == 1
    assert record.wins_b == 0
    assert record.total == 1


def test_ignores_matches_against_other_opponents():
    appearances = [
        _appearance("Alice", "Bob", "W"),
        _appearance("Alice", "Carol", "L"),
    ]
    record = _h2h_from_rows("Alice", "Bob", appearances)
    assert record.total == 1


def test_surface_and_mod_specific_breakdown():
    appearances = [
        _appearance("Alice", "Bob", "W", surface="Clay", mod="vanilla"),
        _appearance("Alice", "Bob", "L", surface="Grass", mod="vanilla"),
        _appearance("Alice", "Bob", "W", surface="Clay", mod="vanilla"),
    ]
    record = _h2h_from_rows("Alice", "Bob", appearances, surface="Clay", mod="vanilla")
    assert record.total == 3
    assert record.specific_total == 2
    assert record.specific_wins_a == 2
    assert record.specific_wins_b == 0


def test_no_surface_mod_filter_leaves_specific_at_zero():
    appearances = [_appearance("Alice", "Bob", "W")]
    record = _h2h_from_rows("Alice", "Bob", appearances)
    assert record.specific_total == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_h2h.py -v`
Expected: FAIL with `ImportError: cannot import name '_h2h_from_rows'`

- [ ] **Step 3: Implement**

In `backend/app/services/stats_service.py`, add near `get_player_details_async` (these are new methods on `StatsService`, plus one new module-level pure function):

```python
    async def _fetch_resolved_appearances_async(self) -> list[dict[str, Any]]:
        """One DB round-trip, alias-resolved, one row per player per match —
        shared by get_h2h_async and the recent-form lookup so a new match's
        first tick costs one query, not two. Does NOT replace the existing
        get_player_details_async / get_player_clusters_async queries (those
        stay as-is per the earlier player-clusters spec's explicit
        decision) — this is a new query for the new win-probability path
        only."""
        alias_map = await self._load_alias_map()
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(
                    FinishedMatch.match_name,
                    FinishedMatch.winner,
                    FinishedMatch.p1_elo,
                    FinishedMatch.p2_elo,
                    FinishedMatch.date,
                    FinishedMatch.surface,
                    FinishedMatch.mod,
                )
            )
            rows = result.all()

        def _is_real(n: str) -> bool:
            return bool(n) and n != "Unknown" and n != "1210967164" and not n.startswith("[.")

        appearances: list[dict[str, Any]] = []
        for row in rows:
            if not row.match_name or " vs " not in row.match_name:
                continue
            raw_p1, raw_p2 = row.match_name.split(" vs ", 1)
            p1 = self._resolve_name(raw_p1.strip(), alias_map)
            p2 = self._resolve_name(raw_p2.strip(), alias_map)
            if not _is_real(p1) or not _is_real(p2):
                continue

            winner_resolved = self._resolve_name(row.winner.strip(), alias_map) if row.winner else None

            def _result_for(name: str) -> str:
                if winner_resolved and winner_resolved.lower() == name.lower():
                    return "W"
                if winner_resolved and winner_resolved.strip():
                    return "L"
                return "?"

            appearances.append({
                "name": p1, "opponent": p2, "result": _result_for(p1),
                "surface": row.surface, "mod": row.mod, "date": row.date,
            })
            appearances.append({
                "name": p2, "opponent": p1, "result": _result_for(p2),
                "surface": row.surface, "mod": row.mod, "date": row.date,
            })
        return appearances

    async def get_h2h_async(self, name_a: str, name_b: str) -> "H2HRecord":
        """Standalone H2H lookup — does its own fetch. The win-probability
        cache path (get_or_compute_pre_match_rates) fetches once and calls
        _h2h_from_rows directly instead, to avoid a second round-trip."""
        appearances = await self._fetch_resolved_appearances_async()
        return _h2h_from_rows(name_a, name_b, appearances)
```

Add the pure module-level helper (near `cluster_list_rows`, at the bottom of the file with the other pure helpers), and the import it needs:

```python
from app.services.win_probability import H2HRecord


def _h2h_from_rows(
    name_a: str,
    name_b: str,
    appearances: list[dict[str, Any]],
    surface: str | None = None,
    mod: str | None = None,
) -> H2HRecord:
    """Pure — filters an already-fetched appearances list to name_a's
    matches against name_b, from name_a's perspective."""
    a_lower, b_lower = name_a.lower(), name_b.lower()
    matches = [
        r for r in appearances
        if r["name"].lower() == a_lower and r["opponent"].lower() == b_lower
    ]
    wins_a = sum(1 for r in matches if r["result"] == "W")
    wins_b = sum(1 for r in matches if r["result"] == "L")
    total = len(matches)

    specific_wins_a = specific_wins_b = specific_total = 0
    if surface is not None and mod is not None:
        specific = [r for r in matches if r.get("surface") == surface and r.get("mod") == mod]
        specific_wins_a = sum(1 for r in specific if r["result"] == "W")
        specific_wins_b = sum(1 for r in specific if r["result"] == "L")
        specific_total = len(specific)

    return H2HRecord(
        wins_a=wins_a, wins_b=wins_b, total=total,
        specific_wins_a=specific_wins_a, specific_wins_b=specific_wins_b,
        specific_total=specific_total,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_h2h.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/stats_service.py backend/tests/test_h2h.py
git commit -m "feat: add H2H lookup with shared appearances query"
```

---

## Task 11: `StatsService` — recent-form win rate

**Files:**
- Modify: `backend/app/services/stats_service.py`
- Test: `backend/tests/test_recent_form.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_recent_form_win_rate(appearances_for_player: list[dict], today: date, window_days: int = 30) -> float | None` — used by `get_or_compute_pre_match_rates` (Task 12).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_recent_form.py
from datetime import date

from app.services.stats_service import _recent_form_win_rate


def _appearance(result, day):
    return {"result": result, "date": date.fromisoformat(day)}


def test_no_matches_returns_none():
    assert _recent_form_win_rate([], today=date(2026, 8, 26)) is None


def test_matches_outside_window_are_excluded():
    old = [_appearance("W", "2026-01-01")]
    assert _recent_form_win_rate(old, today=date(2026, 8, 26)) is None


def test_win_rate_within_window():
    appearances = [
        _appearance("W", "2026-08-20"),
        _appearance("W", "2026-08-15"),
        _appearance("L", "2026-08-10"),
    ]
    rate = _recent_form_win_rate(appearances, today=date(2026, 8, 26))
    assert abs(rate - (2 / 3)) < 1e-9


def test_unknown_results_are_excluded_from_the_denominator():
    appearances = [
        _appearance("W", "2026-08-20"),
        _appearance("?", "2026-08-15"),
    ]
    rate = _recent_form_win_rate(appearances, today=date(2026, 8, 26))
    assert rate == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_recent_form.py -v`
Expected: FAIL with `ImportError: cannot import name '_recent_form_win_rate'`

- [ ] **Step 3: Implement**

Add near `_h2h_from_rows` in `backend/app/services/stats_service.py`:

```python
def _recent_form_win_rate(
    appearances_for_player: list[dict[str, Any]], today: date, window_days: int = 30
) -> float | None:
    """Win rate over a player's matches in the last `window_days`. None if
    there are no matches in that window — the caller treats that as no
    signal, not a 0% form."""
    cutoff = today - timedelta(days=window_days)
    recent = [
        r for r in appearances_for_player
        if r.get("date") and r["date"] >= cutoff and r.get("result") in ("W", "L")
    ]
    if not recent:
        return None
    wins = sum(1 for r in recent if r["result"] == "W")
    return wins / len(recent)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_recent_form.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/stats_service.py backend/tests/test_recent_form.py
git commit -m "feat: add recent-form win-rate helper"
```

---

## Task 12: `StatsService` — pre-match rate cache (`get_or_compute_pre_match_rates`)

**Files:**
- Modify: `backend/app/services/stats_service.py`
- Test: `backend/tests/test_win_prob_cache.py`

**Interfaces:**
- Consumes: `_match_identity_key` (Task 9), `_fetch_resolved_appearances_async`/`_h2h_from_rows` (Task 10), `_recent_form_win_rate` (Task 11), `pre_match_probability`/`form_edge`/`implied_set_win_rate`/`implied_game_win_rate` (Tasks 4, 6).
- Produces: `StatsService.sets_to_win(server: GameServer) -> int` (public — `nb_set` → bo1/bo3/bo5 via the existing `_detect_format`, then → 1/2/3; the single place this mapping lives) and `StatsService.get_or_compute_pre_match_rates(server: GameServer) -> tuple[float, float, float] | None` (returns cached/fresh `(P0, g, s)`, `None` if either ELO is missing/zero) — both called by `ScraperService.fetch_servers()` (Task 13), so the bo1/bo3/bo5 → sets-to-win mapping isn't repeated in `scraper.py`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_win_prob_cache.py
import pytest

from app.models.game_server import GameInfo, GameServer, PlayerConfig, SkillMode, ControlMode
from app.services.stats_service import StatsService


def _server(match_name="Alice vs Bob", elo=1500, other_elo=1500, port=1) -> GameServer:
    """Direct construction, not wire parsing — see the note in
    test_stats_service_identity.py's _make_server for why."""
    return GameServer(
        ip="0.0.0.0",
        port=port,
        match_name=match_name,
        game_info=GameInfo(
            trial=0, player_config=PlayerConfig.SINGLES, nb_set=2,
            skill_mode=SkillMode.INTERMEDIATE, games_per_set=6,
            control_mode=ControlMode.KEYBOARD, preview=0, tiredness=False,
        ),
        max_ping=96, elo=elo, nb_game=3, tag_line="", score="0/0 -- 0:0",
        other_elo=other_elo, give_up_rate=0, reputation=0, surface_name="Clay",
        creation_time_ms=100, is_started=True,
    )


@pytest.mark.asyncio
async def test_missing_elo_returns_none(monkeypatch: pytest.MonkeyPatch):
    service = StatsService()
    server = _server(elo=0, other_elo=1500)
    result = await service.get_or_compute_pre_match_rates(server)
    assert result is None


@pytest.mark.asyncio
async def test_computes_and_caches_on_first_call(monkeypatch: pytest.MonkeyPatch):
    service = StatsService()
    calls = {"n": 0}

    async def _fake_fetch():
        calls["n"] += 1
        return []

    monkeypatch.setattr(service, "_fetch_resolved_appearances_async", _fake_fetch)

    server = _server()
    first = await service.get_or_compute_pre_match_rates(server)
    second = await service.get_or_compute_pre_match_rates(server)

    assert first is not None
    assert first == second
    assert calls["n"] == 1  # DB hit only on the first call


@pytest.mark.asyncio
async def test_cache_survives_name_change(monkeypatch: pytest.MonkeyPatch):
    service = StatsService()

    async def _fake_fetch():
        return []

    monkeypatch.setattr(service, "_fetch_resolved_appearances_async", _fake_fetch)

    waiting = _server(match_name="Waiting vs Bob")
    resolved = _server(match_name="Alice vs Bob")

    first = await service.get_or_compute_pre_match_rates(waiting)
    second = await service.get_or_compute_pre_match_rates(resolved)

    assert first == second
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_win_prob_cache.py -v`
Expected: FAIL with `AttributeError: 'StatsService' object has no attribute 'get_or_compute_pre_match_rates'`

- [ ] **Step 3: Implement**

In `StatsService.__init__` (`backend/app/services/stats_service.py`), add the cache dict alongside `_previous_matches`:

```python
        self._win_prob_cache: dict[tuple, tuple[float, float, float]] = {}
```

Add the `sets_to_win` mapping and the orchestration method, near `get_h2h_async`:

```python
    def sets_to_win(self, server: GameServer) -> int:
        """nb_set -> bo1/bo3/bo5 (via the existing _detect_format) -> sets
        needed to win. The single place this mapping lives — scraper.py
        calls this rather than repeating the bo1/bo3/bo5 dict itself."""
        return {"bo1": 1, "bo3": 2, "bo5": 3}[self._detect_format(server)]

    async def get_or_compute_pre_match_rates(
        self, server: GameServer
    ) -> tuple[float, float, float] | None:
        """Returns cached (P0, g, s) for this match, computing and caching
        it on the first call. None if either player's ELO is missing/zero —
        the caller treats that as "no win probability for this match"."""
        if not server.elo or not server.other_elo:
            return None

        identity = _match_identity_key(server)
        cached = self._win_prob_cache.get(identity)
        if cached is not None:
            return cached

        p1, p2 = server.player_names
        appearances = await self._fetch_resolved_appearances_async()

        h2h = _h2h_from_rows(p1, p2, appearances, surface=server.surface_display, mod=self._detect_mod(server))
        today = self._get_today()
        p1_appearances = [a for a in appearances if a["name"].lower() == p1.lower()]
        p2_appearances = [a for a in appearances if a["name"].lower() == p2.lower()]
        form_a = _recent_form_win_rate(p1_appearances, today)
        form_b = _recent_form_win_rate(p2_appearances, today)

        p0 = pre_match_probability(server.elo, server.other_elo, h2h, form_edge(form_a, form_b))
        s = implied_set_win_rate(p0, self.sets_to_win(server))
        g = implied_game_win_rate(s, server.game_info.games_per_set or 6)

        rates = (p0, g, s)
        self._win_prob_cache[identity] = rates
        return rates
```

Add the new imports at the top of `backend/app/services/stats_service.py`:

```python
from app.services.win_probability import (
    H2HRecord,
    form_edge,
    implied_game_win_rate,
    implied_set_win_rate,
    pre_match_probability,
)
```

(`H2HRecord` import moves here from Task 10 if not already present — keep a single import line, don't duplicate it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_win_prob_cache.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/stats_service.py backend/tests/test_win_prob_cache.py
git commit -m "feat: cache pre-match win-probability rates per match identity"
```

---

## Task 13: Wire into `ScraperService.fetch_servers()`

**Files:**
- Modify: `backend/app/services/scraper.py:143-156`
- Test: `backend/tests/test_scraper_win_probability.py`

**Interfaces:**
- Consumes: `StatsService.get_or_compute_pre_match_rates` (Task 12), `win_probability.live_win_probability` (Task 5), `GameServer.live_state`/`.win_probability` (Task 7).
- Produces: `GameServer.win_probability` set on every eligible broadcast singles server — the last link before the frontend (Task 14).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_scraper_win_probability.py
import pytest

from app.services.scraper import ScraperService

# GameServer's numeric wire tokens (Elo, GameInfo, ...) are parsed via
# safe_int_from_hex — i.e. HEX, not decimal. "64" here is 0x64 = 100
# decimal, "32" is 0x32 = 50 decimal (p1 favored). GameInfo "0" decodes to
# PlayerConfig.SINGLES (all bitfield bits zero); "8" is verified against
# test_parser.py's test_parse_doubles_mode to decode to
# PlayerConfig.COMPETITIVE_DOUBLES (bits 2-4 = 010 = 2).
_SINGLES_GAME_INFO = "0"
_DOUBLES_GAME_INFO = "8"


def _raw_entry(match_name: str, game_info: str, elo: str, other_elo: str) -> str:
    """Builds a 14-token wire-format entry from named fields, in the exact
    order parse_server_entry expects — avoids hand-counting positional
    tokens (a single off-by-one here silently mismatches Elo/OtherElo/
    GiveUpRate/Reputation with no error, only a wrong parsed value)."""
    fields = [
        "0", "1", f'"{match_name}"', game_info, "60", elo, "3", '""',
        '"0/0 -- 0:0"', other_elo, "0", "0", '"Clay"', "64",
    ]
    return " ".join(fields)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value
    return _inner


@pytest.mark.asyncio
async def test_singles_match_gets_win_probability(monkeypatch: pytest.MonkeyPatch):
    service = ScraperService()
    raw = _raw_entry("Alice vs Bob", _SINGLES_GAME_INFO, elo="64", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    server = result.servers[0]
    assert server.win_probability is not None
    assert server.win_probability["p1"] > server.win_probability["p2"]


@pytest.mark.asyncio
async def test_doubles_match_has_no_win_probability(monkeypatch: pytest.MonkeyPatch):
    service = ScraperService()
    raw = _raw_entry("A/B vs C/D", _DOUBLES_GAME_INFO, elo="64", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    assert result.servers[0].win_probability is None


@pytest.mark.asyncio
async def test_missing_elo_has_no_win_probability(monkeypatch: pytest.MonkeyPatch):
    service = ScraperService()
    raw = _raw_entry("Alice vs Bob", _SINGLES_GAME_INFO, elo="0", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    assert result.servers[0].win_probability is None


@pytest.mark.asyncio
async def test_live_state_always_present_regardless_of_win_probability(monkeypatch: pytest.MonkeyPatch):
    service = ScraperService()
    raw = _raw_entry("A/B vs C/D", _DOUBLES_GAME_INFO, elo="64", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    assert result.servers[0].live_state is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_scraper_win_probability.py -v`
Expected: FAIL — `test_singles_match_gets_win_probability` fails with `assert None is not None` (win_probability not wired up yet)

- [ ] **Step 3: Implement**

In `backend/app/services/scraper.py`, add the import at the top:

```python
from app.services.win_probability import live_win_probability
```

Modify `fetch_servers()` — insert the win-probability loop between `servers = list(parse_server_data(raw_data))` (currently line 143) and the `GameServerList(...)` construction (currently line 156):

```python
        servers = list(parse_server_data(raw_data))
        logger.info(f"Parsed {len(servers)} servers")

        from app.services.stats_service import get_stats_service

        stats_service = get_stats_service()

        def _is_real(n: str) -> bool:
            return bool(n) and n != "Unknown" and n != "1210967164" and not n.startswith("[.")

        singles_servers = [
            s for s in servers
            if "doubles" not in s.game_info.mode_display.lower()
            and _is_real(s.player_names[0]) and _is_real(s.player_names[1])
            and s.elo and s.other_elo
        ]

        async def _apply_win_probability(server) -> None:
            rates = await stats_service.get_or_compute_pre_match_rates(server)
            if rates is None or server.live_state is None:
                return
            p0, g, s_rate = rates
            server.win_probability = live_win_probability(
                g, s_rate, server.live_state, stats_service.sets_to_win(server)
            )

        # Concurrent so a burst of simultaneously-new matches costs one
        # round-trip's latency, not N sequential ones.
        await asyncio.gather(*(_apply_win_probability(s) for s in singles_servers))

        # Track finished matches for stats
        if track_stats and servers:
            finished = await stats_service.track_matches(servers)
            if finished > 0:
                logger.info(f"Detected {finished} finished matches")
```

(This replaces the existing `if track_stats and servers: from app.services.stats_service import get_stats_service ...` block — the import moves up, and `stats_service`/the singles filter are now shared with the new win-probability step. The rest of `fetch_servers` — cache assignment, `_update_event` — is unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_scraper_win_probability.py -v`
Expected: PASS (all 4 tests)

Run the full backend suite to confirm no regressions:

Run: `cd backend && pytest -v`
Expected: PASS (all tests, including the pre-existing `test_scraper.py` failure-handling tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scraper.py backend/tests/test_scraper_win_probability.py
git commit -m "feat: wire win-probability computation into scraper poll loop"
```

---

## Task 14: Frontend — consume `live_state`/`win_probability`, drop local score parsing

**Files:**
- Modify: `frontend/src/stores/scores.ts`
- Modify: `frontend/src/components/scores/MatchCard.vue`

**Interfaces:**
- Consumes: `server.live_state` and `server.win_probability` from the WS payload (Task 13).
- Produces: the visible win% bar; no further consumers.

- [ ] **Step 1: Update the store's payload type**

In `frontend/src/stores/scores.ts`, find the TypeScript type/interface for a server entry in the WS payload (matching `GameServer`'s shape) and add:

```typescript
interface LiveMatchState {
  sets: [string, string][]
  sets_won: [number, number]
  current_set_games: [number, number]
  current_points: [string, string] | null
  current_points_numeric: [number, number] | null
  server: number | null
  is_tiebreak: boolean
  games_per_set: number
}

// Within the existing server/GameServer interface, add:
//   live_state: LiveMatchState | null
//   win_probability: { p1: number; p2: number } | null
```

- [ ] **Step 2: Replace `MatchCard.vue`'s local parsing with the server-provided state**

In `frontend/src/components/scores/MatchCard.vue`, delete the `scoreDisplay` computed (currently lines 146-187) and replace every place it was read (`scoreDisplay.sets`, `scoreDisplay.points`, `scoreDisplay.servingPlayer`) with the equivalent from `server.live_state`:

```typescript
// Falls back to the raw score string when live_state is null (unparseable
// score) — matches today's worst case for an unparseable string.
const scoreDisplay = computed(() => {
  const state = props.server.live_state
  if (!state) {
    return { sets: [], points: { p1: '', p2: '' }, servingPlayer: 0 }
  }
  return {
    sets: state.sets.map(([p1, p2]) => ({ p1, p2 })),
    points: state.current_points
      ? { p1: state.current_points[0], p2: state.current_points[1] }
      : { p1: '', p2: '' },
    servingPlayer: state.server ?? 0,
  }
})
```

(This keeps the template's existing `scoreDisplay.sets` / `.points` / `.servingPlayer` references working unchanged — only the computed's implementation changes, from re-parsing the raw string to reading the already-parsed `live_state`.)

- [ ] **Step 3: Add the win% bar**

In the `<script setup>` section, add:

```typescript
const winProbability = computed(() => props.server.win_probability)
```

In the template, inside `.match-grid` (after the two `.player-row` blocks, so it reads as a summary beneath both players):

```html
<div v-if="winProbability" class="win-probability-bar" role="img" :aria-label="`${Math.round(winProbability.p1 * 100)}% vs ${Math.round(winProbability.p2 * 100)}%`">
  <div class="win-probability-fill" :style="{ width: `${winProbability.p1 * 100}%` }"></div>
  <span class="win-probability-label win-probability-label-p1">{{ Math.round(winProbability.p1 * 100) }}%</span>
  <span class="win-probability-label win-probability-label-p2">{{ Math.round(winProbability.p2 * 100) }}%</span>
</div>
```

Add corresponding styles near `.set-score`/`.point-score` in the `<style>` block:

```css
.win-probability-bar {
  position: relative;
  height: 6px;
  border-radius: 3px;
  background: var(--color-border, #333);
  margin-top: 8px;
  overflow: hidden;
}

.win-probability-fill {
  height: 100%;
  background: var(--color-accent, #4a9eff);
  transition: width 0.4s ease;
}

.win-probability-label {
  position: absolute;
  top: -18px;
  font-size: var(--font-size-xs, 11px);
  font-family: var(--font-data);
  color: var(--color-text-secondary, #999);
}

.win-probability-label-p1 { left: 0; }
.win-probability-label-p2 { right: 0; }
```

- [ ] **Step 4: Manual verification in browser**

Run: `cd frontend && npm run dev`

Verify at `localhost:5173`'s Live Scores tab:
- A singles match card shows the % bar, updating on the next poll tick (up to 60s).
- A doubles match card shows the score grid (sets/points/serve dot) exactly as before, but no % bar.
- A match against a bot (`[.` name prefix) or with 0 ELO shows no % bar but still shows the grid.
- Reload the page — no console errors about `live_state`/`win_probability` being undefined.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/scores.ts frontend/src/components/scores/MatchCard.vue
git commit -m "feat: render live win-probability bar; consume server-parsed live state"
```

---

## Self-Review Notes

**Spec coverage:** Every spec section maps to a task — score parsing (Task 1), point/game/tiebreak recursion (Task 2), game/set and set/match recursion (Task 3), inversions (Task 4), live orchestration incl. serve bonus and live-vs-hypothetical tiebreak (Task 5), pre-match blend incl. matched H2H shrinkage (Task 6), `GameServer` schema split between computed/stored fields (Task 7), `surface`/`mod` migration (Task 8), identity-key extraction + stamping (Task 9), H2H with shared appearances query (Task 10), recent form (Task 11), the cache orchestration (Task 12), scraper wiring incl. concurrent new-match lookups (Task 13), frontend consumption and score-parsing deduplication (Task 14).

**Grounding beyond the spec's altitude:** Two gaps only surfaced while writing runnable code, both already folded back into the spec before this plan was written: (1) `LiveMatchState` needed `sets_won`/`current_set_games` as numeric fields, not just raw display strings, so `win_probability.py` never parses score tokens itself; (2) `_race_to_win_prob`'s deuce-equivalent closed form must trigger on *any* tied score at or beyond `target - 1`, not only the literal `(target-1, target-1)` — the "Ad" token maps to a score one point past deuce, and a narrower check lets the recursion re-enter tied states indefinitely from that already-advanced start (Task 2's docstring and test explain this explicitly).

**Type consistency:** `LiveMatchState`, `H2HRecord`, and the `(P0, g, s)` tuple shape are used identically across every task that touches them — verified during writing, no renames drifted between tasks.

**Placeholder scan:** No TBD/TODO — every step has runnable code or an exact shell command.

---

Plan complete and saved to `docs/superpowers/plans/2026-08-26-live-win-probability.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
