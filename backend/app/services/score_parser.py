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

    # Completed sets are those where one player >= games_per_set games.
    # Winner decided by comparing game counts.
    sets_won = [0, 0]
    for p1_raw, p2_raw in sets:
        p1_n, p2_n = _parse_int(p1_raw), _parse_int(p2_raw)
        if p1_n is None or p2_n is None:
            continue
        # Only count as a completed set if one player has >= games_per_set games
        if p1_n >= effective_games_per_set or p2_n >= effective_games_per_set:
            if p1_n > p2_n:
                sets_won[0] += 1
            elif p2_n > p1_n:
                sets_won[1] += 1

    # Current set games: (0, 0) if last set is completed, otherwise the last set's games
    last_p1, last_p2 = sets[-1]
    last_p1_n = _parse_int(last_p1) or 0
    last_p2_n = _parse_int(last_p2) or 0
    if last_p1_n >= effective_games_per_set or last_p2_n >= effective_games_per_set:
        # Last set is completed, so current set hasn't started
        current_set_games = (0, 0)
    else:
        # Last set is in progress
        current_set_games = (last_p1_n, last_p2_n)

    server: int | None = None
    current_raw = current_part.strip()
    if current_raw.startswith("•"):
        server = 2
        current_raw = current_raw[1:]
    elif current_raw.endswith("•"):
        server = 1
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
