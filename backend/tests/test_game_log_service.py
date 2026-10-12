from sqlalchemy import select

from app.models.match_game_event import MatchGameEvent
from app.services import game_log_service
from app.services.game_log_service import GameLogService
from app.services.score_parser import LiveMatchState


def _state(
    sets_won=(0, 0),
    current_set_games=(0, 0),
    current_points=None,
    server=None,
    is_tiebreak=False,
) -> LiveMatchState:
    return LiveMatchState(
        sets=[],
        sets_won=sets_won,
        current_set_games=current_set_games,
        current_points=current_points,
        current_points_numeric=None,
        server=server,
        is_tiebreak=is_tiebreak,
        games_per_set=6,
    )


def _replay(snapshots, match_id="m") -> list[MatchGameEvent]:
    svc = GameLogService()
    return [e for s in snapshots if (e := svc.step(match_id, s))]


def _fields(event: MatchGameEvent) -> dict:
    return {
        "match_id": event.match_id,
        "set_number": event.set_number,
        "game_number": event.game_number,
        "p1_games": event.p1_games,
        "p2_games": event.p2_games,
        "winner": event.winner,
        "server": event.server,
        "is_tiebreak": event.is_tiebreak,
        "points": event.points,
    }


def test_no_change_between_ticks_emits_nothing():
    snapshots = [_state(current_set_games=(2, 1)), _state(current_set_games=(2, 1))]
    assert _replay(snapshots) == []


def test_p1_wins_game_mid_set():
    events = _replay(
        [
            _state(current_set_games=(2, 1), server=1),
            _state(current_set_games=(3, 1), server=2),
        ]
    )
    assert [_fields(e) for e in events] == [
        {
            "match_id": "m",
            "set_number": 1,
            "game_number": 4,
            "p1_games": 3,
            "p2_games": 1,
            "winner": 1,
            "server": 1,
            "is_tiebreak": False,
            "points": [],
        }
    ]


def test_p2_wins_game_mid_set():
    events = _replay(
        [
            _state(current_set_games=(4, 5), server=2),
            _state(current_set_games=(4, 6), server=1),
        ]
    )
    assert [_fields(e) for e in events] == [
        {
            "match_id": "m",
            "set_number": 1,
            "game_number": 10,
            "p1_games": 4,
            "p2_games": 6,
            "winner": 2,
            "server": 2,
            "is_tiebreak": False,
            "points": [],
        }
    ]


def test_set_closed_by_games():
    events = _replay(
        [
            _state(sets_won=(0, 0), current_set_games=(5, 3), server=1),
            _state(sets_won=(1, 0), current_set_games=(0, 0), server=2),
        ]
    )
    assert [_fields(e) for e in events] == [
        {
            "match_id": "m",
            "set_number": 1,
            "game_number": 9,
            "p1_games": 6,
            "p2_games": 3,
            "winner": 1,
            "server": 1,
            "is_tiebreak": False,
            "points": [],
        }
    ]


def test_set_closed_by_tiebreak():
    events = _replay(
        [
            _state(
                sets_won=(0, 1),
                current_set_games=(6, 6),
                current_points=("3", "6"),
                server=2,
                is_tiebreak=True,
            ),
            _state(sets_won=(1, 1), current_set_games=(0, 0), server=1),
        ]
    )
    assert [_fields(e) for e in events] == [
        {
            "match_id": "m",
            "set_number": 2,
            "game_number": 13,
            "p1_games": 7,
            "p2_games": 6,
            "winner": 1,
            "server": 2,
            "is_tiebreak": True,
            "points": ["3-6"],
        }
    ]


def test_second_set_numbering():
    events = _replay(
        [
            _state(sets_won=(1, 0), current_set_games=(3, 2), server=1),
            _state(sets_won=(1, 0), current_set_games=(4, 2), server=2),
        ]
    )
    assert [(e.set_number, e.game_number, e.p1_games, e.p2_games) for e in events] == [
        (2, 6, 4, 2)
    ]


def test_first_sighting_emits_nothing_even_mid_game():
    svc = GameLogService()
    assert (
        svc.step("m", _state(current_set_games=(3, 2), current_points=("30", "15")))
        is None
    )


def test_point_trail_dedupes_repeats_and_closes_with_the_game():
    events = _replay(
        [
            _state(current_points=("0", "0"), server=1),
            _state(current_points=("15", "0"), server=1),
            _state(current_points=("15", "0"), server=1),
            _state(current_points=("30", "15"), server=1),
            _state(current_points=("40", "15"), server=1),
            _state(current_set_games=(1, 0), current_points=None, server=2),
        ]
    )
    assert [e.points for e in events] == [["0-0", "15-0", "30-15", "40-15"]]


def test_point_trail_resets_between_games():
    events = _replay(
        [
            _state(current_points=("0", "0")),
            _state(current_points=("40", "0")),
            _state(current_set_games=(1, 0), current_points=None),
            _state(current_set_games=(1, 0), current_points=("0", "0")),
            _state(current_set_games=(1, 0), current_points=("15", "0")),
            _state(current_set_games=(2, 0), current_points=None),
        ]
    )
    assert [e.points for e in events] == [["0-0", "40-0"], ["0-0", "15-0"]]


def test_game_closing_without_observed_points_has_empty_trail():
    events = _replay(
        [
            _state(current_set_games=(0, 0)),
            _state(current_set_games=(1, 0)),
        ]
    )
    assert [e.points for e in events] == [[]]


async def _rows(factory) -> list[dict]:
    async with factory() as session:
        result = await session.execute(
            select(MatchGameEvent).order_by(
                MatchGameEvent.set_number, MatchGameEvent.game_number
            )
        )
        return [_fields(e) for e in result.scalars()]


async def test_record_tick_persists_a_closed_game_once(
    sqlite_session_factory, monkeypatch
):
    monkeypatch.setattr(
        game_log_service, "get_session_factory", lambda: sqlite_session_factory
    )
    before = _state(current_points=("40", "15"), server=1)
    after = _state(current_set_games=(1, 0), server=2)

    first_run = GameLogService()
    await first_run.record_tick({"m": before})
    await first_run.record_tick({"m": after})
    restarted = GameLogService()
    await restarted.record_tick({"m": before})
    await restarted.record_tick({"m": after})

    assert await _rows(sqlite_session_factory) == [
        {
            "match_id": "m",
            "set_number": 1,
            "game_number": 1,
            "p1_games": 1,
            "p2_games": 0,
            "winner": 1,
            "server": 1,
            "is_tiebreak": False,
            "points": ["40-15"],
        }
    ]


async def test_record_tick_forgets_matches_missing_from_the_tick():
    svc = GameLogService()
    await svc.record_tick({"m": _state()})
    assert set(svc._tracked) == {"m"}

    await svc.record_tick({})

    assert svc._tracked == {}
