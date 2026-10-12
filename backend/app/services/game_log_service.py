"""Records completed games of live singles matches.

The master server only exposes a current-state snapshot per poll, so a game is
detected by diffing consecutive snapshots of a match. The point trail of each
game holds the distinct point scores polling happened to observe, and is
therefore best effort.
"""

from dataclasses import dataclass

from app.models.match_game_event import MatchGameEvent
from app.services.score_parser import LiveMatchState


@dataclass
class _Tracked:
    state: LiveMatchState
    points: list[str]


def diff_game(
    match_id: str,
    previous: LiveMatchState,
    current: LiveMatchState,
    points: list[str],
) -> MatchGameEvent | None:
    prev_sets, curr_sets = sum(previous.sets_won), sum(current.sets_won)
    prev_games, curr_games = previous.current_set_games, current.current_set_games

    if curr_sets > prev_sets:
        set_number = prev_sets + 1
        winner = 1 if current.sets_won[0] > previous.sets_won[0] else 2
    elif curr_sets == prev_sets and sum(curr_games) > sum(prev_games):
        set_number = curr_sets + 1
        winner = 1 if curr_games[0] > prev_games[0] else 2
    else:
        return None

    p1, p2 = prev_games
    if winner == 1:
        p1 += 1
    else:
        p2 += 1

    return MatchGameEvent(
        match_id=match_id,
        set_number=set_number,
        game_number=p1 + p2,
        p1_games=p1,
        p2_games=p2,
        winner=winner,
        server=previous.server,
        is_tiebreak=previous.is_tiebreak,
        points=points,
    )


class GameLogService:
    def __init__(self) -> None:
        self._tracked: dict[str, _Tracked] = {}

    def step(self, match_id: str, current: LiveMatchState) -> MatchGameEvent | None:
        tracked = self._tracked.get(match_id)
        trail = tracked.points if tracked else []
        event = diff_game(match_id, tracked.state, current, trail) if tracked else None
        if event:
            trail = []
        if current.current_points:
            snap = f"{current.current_points[0]}-{current.current_points[1]}"
            if not trail or trail[-1] != snap:
                trail.append(snap)
        self._tracked[match_id] = _Tracked(current, trail)
        return event
