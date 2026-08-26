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
