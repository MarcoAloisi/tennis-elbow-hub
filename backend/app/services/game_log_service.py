"""Records completed games of live singles matches.

The master server only exposes a current-state snapshot per poll, so a game is
detected by diffing consecutive snapshots of a match. The point trail of each
game holds the distinct point scores polling happened to observe, and is
therefore best effort. The trail leaves out the 0-0 start and tags break (BP),
set (SP) and match (MP) points.
"""

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.core.database import get_session_factory
from app.core.logging import get_logger
from app.models.match_game_event import MatchGameEvent
from app.services.score_parser import LiveMatchState

logger = get_logger("game_log")


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


def _point_label(state: LiveMatchState, sets_to_win: int) -> str:
    """BP, SP and MP for the point score `state` shows, '' when none apply.

    The point leader holds game point when one more point wins the game, in a
    tiebreak (to 7, win by 2) or a regular game. That is a break point when the
    leader is the receiver, a set point when the game also wins the set and a
    match point when the set also wins the match. A tiebreak has no break points.
    """
    points = state.current_points_numeric
    if points is None or points[0] == points[1]:
        return ""
    leader = 0 if points[0] > points[1] else 1
    ahead, behind = points[leader], points[1 - leader]
    if state.is_tiebreak:
        game_point = ahead >= 6
    else:
        game_point = ahead == 4 or (ahead == 3 and behind < 3)
    if not game_point:
        return ""

    games = list(state.current_set_games)
    games[leader] += 1
    wins_set = state.is_tiebreak or (
        games[leader] >= state.games_per_set and games[leader] - games[1 - leader] >= 2
    )
    labels = []
    if wins_set:
        labels.append("MP" if state.sets_won[leader] + 1 >= sets_to_win else "SP")
    if not state.is_tiebreak and state.server not in (None, leader + 1):
        labels.append("BP")
    return " ".join(labels)


class GameLogService:
    def __init__(self) -> None:
        self._tracked: dict[str, _Tracked] = {}

    def step(
        self, match_id: str, current: LiveMatchState, sets_to_win: int
    ) -> MatchGameEvent | None:
        tracked = self._tracked.get(match_id)
        trail = tracked.points if tracked else []
        event = diff_game(match_id, tracked.state, current, trail) if tracked else None
        if event:
            trail = []
        points = current.current_points
        if points and current.current_points_numeric != (0, 0):
            entry = (
                f"{points[0]}-{points[1]} {_point_label(current, sets_to_win)}".strip()
            )
            if not trail or trail[-1] != entry:
                trail.append(entry)
        self._tracked[match_id] = _Tracked(current, trail)
        return event

    def trail(self, match_id: str) -> list[str]:
        tracked = self._tracked.get(match_id)
        return list(tracked.points) if tracked else []

    async def record_tick(
        self, states: dict[str, LiveMatchState], sets_to_win: dict[str, int]
    ) -> None:
        events = [
            e
            for mid, cur in states.items()
            if (e := self.step(mid, cur, sets_to_win[mid]))
        ]
        for stale in self._tracked.keys() - states.keys():
            del self._tracked[stale]
        for event in events:
            await self._insert(event)

    async def _insert(self, event: MatchGameEvent) -> None:
        async with get_session_factory()() as session:
            try:
                session.add(event)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.debug(
                    f"game already recorded: {event.match_id} "
                    f"set {event.set_number} game {event.game_number}"
                )
            except Exception as e:
                await session.rollback()
                logger.error(f"failed to record game for {event.match_id}: {e}")


_game_log_service: GameLogService | None = None


def get_game_log_service() -> GameLogService:
    global _game_log_service
    if _game_log_service is None:
        _game_log_service = GameLogService()
    return _game_log_service
