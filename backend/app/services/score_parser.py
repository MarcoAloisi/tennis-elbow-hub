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
    """Returns None if `score` has no set segments — caller falls back gracefully.

    A missing " -- " separator (e.g. a bare "0/0" for a not-yet-started
    match) does NOT by itself mean unparseable — the whole string is tried
    as the sets segment, with no current-game segment. Only a string with
    no valid `/`-containing set tokens at all (e.g. "", "..." or "garbage")
    returns None.
    """
    if not score:
        return None

    if " -- " in score:
        sets_part, _, current_part = score.partition(" -- ")
    else:
        sets_part, current_part = score, ""

    sets: list[tuple[str, str]] = []
    for token in sets_part.strip().split():
        if "/" not in token:
            continue
        p1, p2 = token.split("/", 1)
        sets.append((p1, p2))

    if not sets:
        return None

    effective_games_per_set = games_per_set if games_per_set > 0 else 6

    # Helper to check if a set is won by a player (with win-by-2 margin)
    def is_set_won(p1_games: int, p2_games: int) -> int | None:
        """Returns 1 if P1 won, 2 if P2 won, None if set is in progress."""
        # Standard win: reach games_per_set with 2+ game margin
        if p1_games >= effective_games_per_set and p1_games - p2_games >= 2:
            return 1
        if p2_games >= effective_games_per_set and p2_games - p1_games >= 2:
            return 2
        # Tiebreak win: exactly games_per_set + 1 while opponent has games_per_set
        if p1_games == effective_games_per_set + 1 and p2_games == effective_games_per_set:
            return 1
        if p2_games == effective_games_per_set + 1 and p1_games == effective_games_per_set:
            return 2
        return None

    sets_won = [0, 0]
    current_set_games = (0, 0)

    for i, (p1_raw, p2_raw) in enumerate(sets):
        p1_n, p2_n = _parse_int(p1_raw), _parse_int(p2_raw)
        if p1_n is None or p2_n is None:
            continue

        winner = is_set_won(p1_n, p2_n)
        is_last_set = i == len(sets) - 1

        if winner:
            # This set is completed
            if winner == 1:
                sets_won[0] += 1
            else:
                sets_won[1] += 1
            if is_last_set:
                # Last set is complete, so next set hasn't started
                current_set_games = (0, 0)
        else:
            # This set is in progress
            if is_last_set:
                # Last set is the current set
                current_set_games = (p1_n, p2_n)

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
