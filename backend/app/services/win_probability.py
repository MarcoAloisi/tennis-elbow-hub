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
