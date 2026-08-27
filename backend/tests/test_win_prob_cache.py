import pytest

from app.models.game_server import (
    ControlMode,
    GameInfo,
    GameServer,
    PlayerConfig,
    SkillMode,
)
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
