import pytest

from app.services.scraper import ScraperService

# GameServer's numeric wire tokens (Elo, GameInfo, ...) are parsed via
# safe_int_from_hex — i.e. HEX, not decimal. "64" here is 0x64 = 100
# decimal, "32" is 0x32 = 50 decimal (p1 favored). GameInfo "0" decodes to
# PlayerConfig.SINGLES (all bitfield bits zero); "8" is verified against
# test_parser.py's test_parse_doubles_mode to decode to
# PlayerConfig.COMPETITIVE_DOUBLES (bits 2-4 = 010 = 2).
_SINGLES_GAME_INFO = "0"
_DOUBLES_GAME_INFO = "8"
# player_cfg_raw = (value >> 2) & 0x7 == 1 -> PlayerConfig.UNKNOWN_1.
# value=4 (0b100) >> 2 == 1.
_UNKNOWN_GAME_INFO = "4"


def _raw_entry(match_name: str, game_info: str, elo: str, other_elo: str) -> str:
    """Builds a 14-token wire-format entry from named fields, in the exact
    order parse_server_entry expects — avoids hand-counting positional
    tokens (a single off-by-one here silently mismatches Elo/OtherElo/
    GiveUpRate/Reputation with no error, only a wrong parsed value)."""
    fields = [
        "0", "1", f'"{match_name}"', game_info, "60", elo, "3", '""',
        '"0/0 -- 0:0"', other_elo, "0", "0", '"Clay"', "64",
    ]
    return " ".join(fields)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value
    return _inner


@pytest.mark.asyncio
async def test_singles_match_gets_win_probability(monkeypatch: pytest.MonkeyPatch):
    service = ScraperService()
    raw = _raw_entry("Alice vs Bob", _SINGLES_GAME_INFO, elo="64", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    server = result.servers[0]
    assert server.win_probability is not None
    assert server.win_probability["p1"] > server.win_probability["p2"]


@pytest.mark.asyncio
async def test_doubles_match_has_no_win_probability(monkeypatch: pytest.MonkeyPatch):
    service = ScraperService()
    raw = _raw_entry("A/B vs C/D", _DOUBLES_GAME_INFO, elo="64", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    assert result.servers[0].win_probability is None


@pytest.mark.asyncio
async def test_missing_elo_has_no_win_probability(monkeypatch: pytest.MonkeyPatch):
    service = ScraperService()
    raw = _raw_entry("Alice vs Bob", _SINGLES_GAME_INFO, elo="0", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    assert result.servers[0].win_probability is None


@pytest.mark.asyncio
async def test_live_state_always_present_regardless_of_win_probability(monkeypatch: pytest.MonkeyPatch):
    service = ScraperService()
    raw = _raw_entry("A/B vs C/D", _DOUBLES_GAME_INFO, elo="64", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    assert result.servers[0].live_state is not None


@pytest.mark.asyncio
async def test_unknown_player_config_has_no_win_probability(monkeypatch: pytest.MonkeyPatch):
    """An unrecognized player_config (UNKNOWN_1) displays as "Unknown" via
    mode_display, which contains no "doubles" substring — checking the
    actual enum (PlayerConfig.SINGLES) rather than the display string is
    what keeps this out of the win-probability path (fix #6)."""
    service = ScraperService()
    raw = _raw_entry("Alice vs Bob", _UNKNOWN_GAME_INFO, elo="64", other_elo="32")
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    result = await service.fetch_servers(track_stats=False)

    server = result.servers[0]
    from app.models.game_server import PlayerConfig

    assert server.game_info.player_config == PlayerConfig.UNKNOWN_1
    assert server.win_probability is None


@pytest.mark.asyncio
async def test_appearances_fetched_at_most_once_per_tick(monkeypatch: pytest.MonkeyPatch):
    """Multiple singles servers, all cache-misses, in one fetch_servers()
    call must share a single _fetch_resolved_appearances_async() call —
    not one full-table scan per match (fix #5)."""
    service = ScraperService()

    entry_1 = _raw_entry("Alice vs Bob", _SINGLES_GAME_INFO, elo="64", other_elo="32")
    entry_2 = _raw_entry("Carol vs Dave", _SINGLES_GAME_INFO, elo="32", other_elo="64")
    raw = entry_1 + "\n" + entry_2
    monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw))

    from app.services import stats_service as stats_service_module

    calls = {"n": 0}
    stats_service = stats_service_module.get_stats_service()

    async def _fake_fetch():
        calls["n"] += 1
        return []

    monkeypatch.setattr(stats_service, "_fetch_resolved_appearances_async", _fake_fetch)

    result = await service.fetch_servers(track_stats=False)

    assert len(result.servers) == 2
    assert all(s.win_probability is not None for s in result.servers)
    assert calls["n"] == 1
