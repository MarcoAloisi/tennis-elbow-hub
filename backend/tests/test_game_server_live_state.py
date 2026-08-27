from app.services.parser import parse_server_data

# Reuses the exact wire-format sample from conftest.py's sample_server_data
# fixture (GameInfo=0x1B198E41, which decodes to games_per_set=6) rather
# than hand-rolling a new one — GameServer's numeric fields (elo, port,
# GameInfo, ...) are parsed via safe_int_from_hex, i.e. HEX, not decimal,
# so a hand-written "elo=1600"-style token would silently parse as 0x1600
# (5632). Going through the real tokenizer with known-good data sidesteps
# that entirely.
_SAMPLE = (
    '0 E9FD "RBI vs TestPlayer" 1B198E41 96 415 3 "XKT v4.2d" '
    '"6/3 4/6 1/1 -- 00:40•" 393 0 1 "BlueGreenCement" 69760194'
)


def _parse_one(raw: str):
    servers = list(parse_server_data(raw))
    assert len(servers) == 1
    return servers[0]


def test_live_state_is_present_on_every_server():
    server = _parse_one(_SAMPLE)
    assert server.live_state is not None
    assert server.live_state.sets == [("6", "3"), ("4", "6"), ("1", "1")]
    assert server.live_state.server == 2


def test_live_state_uses_games_per_set_from_game_info():
    server = _parse_one(_SAMPLE)
    assert server.game_info.games_per_set == 6
    assert server.live_state.games_per_set == 6


def test_win_probability_defaults_to_none():
    server = _parse_one(_SAMPLE)
    assert server.win_probability is None


def test_win_probability_is_settable_and_serializes():
    server = _parse_one(_SAMPLE)
    server.win_probability = {"p1": 0.62, "p2": 0.38}
    dumped = server.model_dump()
    assert dumped["win_probability"] == {"p1": 0.62, "p2": 0.38}
    assert "live_state" in dumped
