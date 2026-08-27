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
