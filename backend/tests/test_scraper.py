"""Tests for the ScraperService."""

import asyncio

import pytest

from app.services import scraper as scraper_module
from app.services import stats_service as stats_service_module
from app.services.score_parser import LiveMatchState
from app.services.scraper import ScraperService
from tests.test_scraper_win_probability import (
    _DOUBLES_GAME_INFO,
    _SINGLES_GAME_INFO,
    _raw_entry,
)


class TestFetchServersFailureHandling:
    """A failed upstream fetch must not blank out the last known good data."""

    @pytest.mark.asyncio
    async def test_failed_fetch_keeps_previous_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ScraperService()

        # Seed the cache with a successful fetch.
        raw_data = '0 0 "A vs B" 0 0 0 0 "" "0-0" 0 0 0 "Clay" 1'
        monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw_data))
        first = await service.fetch_servers(track_stats=False)
        assert first.total == 1

        # Simulate a transient upstream failure.
        monkeypatch.setattr(service, "fetch_raw_data", _async_return(None))
        second = await service.fetch_servers(track_stats=False)

        assert second.total == 1
        assert second is service.get_latest_data()
        assert service.get_latest_data().total == 1

    @pytest.mark.asyncio
    async def test_failed_fetch_does_not_notify_listeners(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ScraperService()
        monkeypatch.setattr(service, "fetch_raw_data", _async_return(None))

        waiter = asyncio.ensure_future(service.wait_for_update())
        await service.fetch_servers(track_stats=False)

        # A failed fetch must not wake up WebSocket listeners waiting for new data.
        done, pending = await asyncio.wait([waiter], timeout=0.05)
        assert waiter in pending
        waiter.cancel()


class _RecordingGameLog:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, LiveMatchState]] = []
        self.sets_to_win: list[dict[str, int]] = []
        self._error = error

    async def record_tick(
        self, states: dict[str, LiveMatchState], sets_to_win: dict[str, int]
    ) -> None:
        self.calls.append(states)
        self.sets_to_win.append(sets_to_win)
        if self._error:
            raise self._error

    def trail(self, match_id: str) -> list[str]:
        return ["0-0", "15-0"]


async def _fetch_with_game_log(monkeypatch, game_log, *, track_stats: bool):
    service = ScraperService()
    raw = "\n".join(
        [
            _raw_entry("Alice vs Bob", _SINGLES_GAME_INFO, elo="64", other_elo="32"),
            _raw_entry("A/B vs C/D", _DOUBLES_GAME_INFO, elo="64", other_elo="32"),
        ]
    )
    stats_service = stats_service_module.get_stats_service()
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))
    monkeypatch.setattr(
        stats_service, "_fetch_resolved_appearances_async", _async_return([])
    )

    async def _no_finished_matches(servers):
        return 0

    monkeypatch.setattr(stats_service, "track_matches", _no_finished_matches)
    monkeypatch.setattr(scraper_module, "get_game_log_service", lambda: game_log)
    return await service.fetch_servers(track_stats=track_stats)


class TestGameLogWiring:
    async def test_singles_live_states_are_recorded_once_per_tick(self, monkeypatch):
        game_log = _RecordingGameLog()

        result = await _fetch_with_game_log(monkeypatch, game_log, track_stats=True)

        singles_id = next(
            s.match_id for s in result.servers if s.player_names[0] == "Alice"
        )
        assert len(game_log.calls) == 1
        assert list(game_log.calls[0]) == [singles_id]
        assert game_log.calls[0][singles_id].current_points == ("0", "0")
        assert game_log.sets_to_win == [{singles_id: 1}]

    async def test_singles_servers_carry_the_live_point_trail(self, monkeypatch):
        result = await _fetch_with_game_log(
            monkeypatch, _RecordingGameLog(), track_stats=True
        )

        trails = {s.player_names[0]: s.point_trail for s in result.servers}
        assert trails == {"Alice": ["0-0", "15-0"], "A/B": None}

    async def test_not_recorded_when_stats_tracking_is_off(self, monkeypatch):
        game_log = _RecordingGameLog()

        await _fetch_with_game_log(monkeypatch, game_log, track_stats=False)

        assert game_log.calls == []

    async def test_game_log_failure_does_not_break_the_tick(self, monkeypatch):
        game_log = _RecordingGameLog(error=RuntimeError("db down"))

        result = await _fetch_with_game_log(monkeypatch, game_log, track_stats=True)

        assert result.total == 2
        assert len(game_log.calls) == 1


def _async_return(value):
    async def _inner() -> object:
        return value

    return _inner
