"""Live tennis win-probability math: point -> game -> set -> match.

Pure functions, no DB access. `pre_match_probability`'s inputs (ELO, H2H,
recent form) are fetched and cached once per match by StatsService — see
`get_or_compute_pre_match_rates` there. Everything in this module consumes
plain integers only; score_parser.py is the sole owner of raw score-token
interpretation.
"""

import math
from dataclasses import dataclass

from app.services.score_parser import LiveMatchState


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
    if games_a == games_per_set and games_b == games_per_set:
        # Tied at games_per_set-all: this IS the (possibly live) tiebreak —
        # game_prob_a already reflects the real tiebreak point score via
        # point_to_tiebreak_prob upstream, if one is available.
        return game_prob_a
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


# Task 6: Pre-match probability blend (H2H + form + ELO)


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
