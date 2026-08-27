from app.models.game_server import (
    ControlMode,
    GameInfo,
    GameServer,
    PlayerConfig,
    SkillMode,
)
from app.services.stats_service import _match_identity_key


def _make_server(match_name: str, port: int = 1, creation_time_ms: int = 100) -> GameServer:
    """Constructs a GameServer directly, bypassing wire-format parsing —
    this test only cares about the identity fields, not the hex tokenizer,
    and GameServer's numeric wire fields are parsed as hex by the real
    parser (safe_int_from_hex), so hand-written decimal-looking raw strings
    would silently parse wrong. Direct construction sidesteps that."""
    return GameServer(
        ip="0.0.0.0",
        port=port,
        match_name=match_name,
        game_info=GameInfo(
            trial=0, player_config=PlayerConfig.SINGLES, nb_set=2,
            skill_mode=SkillMode.INTERMEDIATE, games_per_set=6,
            control_mode=ControlMode.KEYBOARD, preview=0, tiredness=False,
        ),
        max_ping=96, elo=1500, nb_game=3, tag_line="", score="0/0 -- 0:0",
        other_elo=1500, give_up_rate=0, reputation=0, surface_name="Clay",
        creation_time_ms=creation_time_ms, is_started=True,
    )


def test_identity_key_excludes_match_name():
    """A name resolving mid-match (e.g. 'Waiting' -> real name) must not
    change the identity key — that's what makes the win-probability cache
    (and the existing rename-detection logic) survive it."""
    server_a = _make_server("Waiting vs Bob")
    server_b = _make_server("Alice vs Bob")
    assert _match_identity_key(server_a) == _match_identity_key(server_b)


def test_identity_key_differs_on_port():
    server_a = _make_server("Alice vs Bob", port=1)
    server_b = _make_server("Alice vs Bob", port=2)
    assert _match_identity_key(server_a) != _match_identity_key(server_b)
