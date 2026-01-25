"""Parser service for Tennis Elbow 4 server data.

This module handles parsing of the hex-encoded server data format
and the GameInfo bitfield structure.
"""

import re
from typing import Generator

from app.core.logging import get_logger
from app.core.security import safe_int_from_hex
from app.models.game_server import (
    ControlMode,
    GameInfo,
    GameServer,
    PlayerConfig,
    SkillMode,
)

logger = get_logger("parser")


def parse_game_info_bitfield(value: int) -> GameInfo:
    """Parse the GameInfo hex value into structured data.

    Bitfield layout (28 bits):
    - Bits 0-1: Trial (2 bits)
    - Bits 2-4: PlayerCfg (3 bits)
    - Bits 5-6: NbSet (2 bits)
    - Bits 7-8: SkillMode (2 bits)
    - Bits 9-17: Empty/reserved (9 bits)
    - Bits 18-20: GamePerSet (3 bits)
    - Bit 21: Unused (1 bit)
    - Bits 22-23: ControlMode (2 bits)
    - Bits 24-26: Preview (3 bits)
    - Bit 27: Tiredness (1 bit)

    Args:
        value: Integer value from hex GameInfo field.

    Returns:
        Parsed GameInfo model with all fields extracted.
    """
    # Extract each field using bit masking and shifting
    trial = (value >> 0) & 0x3  # 2 bits
    player_cfg_raw = (value >> 2) & 0x7  # 3 bits
    nb_set = (value >> 5) & 0x3  # 2 bits
    skill_mode_raw = (value >> 7) & 0x3  # 2 bits
    # bits 9-17 are empty (9 bits)
    games_per_set = (value >> 18) & 0x7  # 3 bits
    # bit 21 is unused
    control_mode_raw = (value >> 22) & 0x3  # 2 bits
    preview = (value >> 24) & 0x7  # 3 bits
    tiredness = bool((value >> 27) & 0x1)  # 1 bit

    # Convert raw values to enums with bounds checking
    try:
        player_config = PlayerConfig(player_cfg_raw)
    except ValueError:
        player_config = PlayerConfig.SINGLES

    try:
        skill_mode = SkillMode(skill_mode_raw)
    except ValueError:
        skill_mode = SkillMode.INTERMEDIATE

    try:
        control_mode = ControlMode(control_mode_raw)
    except ValueError:
        control_mode = ControlMode.KEYBOARD

    return GameInfo(
        trial=trial,
        player_config=player_config,
        nb_set=nb_set,
        skill_mode=skill_mode,
        games_per_set=games_per_set,
        control_mode=control_mode,
        preview=preview,
        tiredness=tiredness,
    )


# Regex pattern to match server entry components
# Matches: hex_value "quoted_string" or standalone hex_value
SERVER_PATTERN = re.compile(
    r'"([^"]*)"'  # Quoted strings
    r"|"
    r"([0-9A-Fa-f]+)"  # Hex values
    r"|"
    r"(\*)"  # Asterisk marker
    r"|"
    r"([0-9.]+)"  # IP-like values
)


def tokenize_server_line(line: str) -> list[str]:
    """Tokenize a server entry line into components.

    Args:
        line: Raw server entry line.

    Returns:
        List of tokens (strings and hex values).
    """
    tokens = []
    for match in SERVER_PATTERN.finditer(line):
        # Get the first non-None group
        token = match.group(1) or match.group(2) or match.group(3) or match.group(4)
        if token is not None:
            tokens.append(token)
    return tokens


def parse_server_entry(tokens: list[str]) -> GameServer | None:
    """Parse tokenized server entry into GameServer model.

    Expected token order:
    0: IP (0 if started, or x.x.x.x)
    1: Port (hex)
    2: "MatchName"
    3: GameInfo (hex)
    4: MaxPing (hex)
    5: Elo (hex)
    6: NbGame (hex)
    7: "TagLine"
    8: "Score"
    9: OtherElo (hex)
    10: GiveUpRate (hex)
    11: Reputation (hex)
    12: "SurfaceName"
    13: CreationTimeMs (hex)

    Args:
        tokens: List of parsed tokens.

    Returns:
        GameServer model or None if parsing fails.
    """
    try:
        # Need at least 14 tokens for a complete entry
        if len(tokens) < 14:
            logger.warning(f"Incomplete server entry: {len(tokens)} tokens")
            return None

        # Parse IP - "0" means match started
        ip_raw = tokens[0]
        is_started = ip_raw == "0"
        ip = "0.0.0.0" if is_started else ip_raw

        # Parse numeric fields from hex
        port = safe_int_from_hex(tokens[1])
        match_name = tokens[2]
        game_info_raw = safe_int_from_hex(tokens[3])
        max_ping = safe_int_from_hex(tokens[4])
        elo = safe_int_from_hex(tokens[5])
        nb_game = safe_int_from_hex(tokens[6])
        tag_line = tokens[7]
        score = tokens[8]
        other_elo = safe_int_from_hex(tokens[9])
        give_up_rate = safe_int_from_hex(tokens[10])
        reputation = safe_int_from_hex(tokens[11])
        surface_name = tokens[12]
        creation_time_ms = safe_int_from_hex(tokens[13])

        # Parse GameInfo bitfield
        game_info = parse_game_info_bitfield(game_info_raw)

        return GameServer(
            ip=ip,
            port=port,
            match_name=match_name,
            game_info=game_info,
            max_ping=max_ping,
            elo=elo,
            nb_game=nb_game,
            tag_line=tag_line,
            score=score,
            other_elo=other_elo,
            give_up_rate=give_up_rate,
            reputation=reputation,
            surface_name=surface_name,
            creation_time_ms=creation_time_ms,
            is_started=is_started,
        )

    except Exception as e:
        logger.error(f"Failed to parse server entry: {e}")
        return None


def parse_server_data(raw_data: str) -> Generator[GameServer, None, None]:
    """Parse raw server data into GameServer models.

    The data format contains multiple server entries in a single string,
    separated by specific markers or patterns.

    Args:
        raw_data: Raw server data string from the source.

    Yields:
        Parsed GameServer models.
    """
    # Split data by common patterns that indicate new entries
    # Look for patterns like "0 " or IP addresses at the start
    current_tokens: list[str] = []
    all_tokens = tokenize_server_line(raw_data)

    # Process tokens and identify server boundaries
    # Server entries start with IP (0, *, or IP address) followed by port
    i = 0
    while i < len(all_tokens):
        token = all_tokens[i]

        # Check for server entry boundary
        # Entries typically start with 0, *, or an IP-like pattern
        is_boundary = (
            token in ("0", "*", "0.0.0.0")
            or re.match(r"^\d+\.\d+\.\d+\.\d+$", token)
            or (
                current_tokens
                and len(current_tokens) >= 14
                and re.match(r"^[0-9A-Fa-f]+$", token)
                and i + 1 < len(all_tokens)
            )
        )

        if is_boundary and current_tokens and len(current_tokens) >= 14:
            # Parse current entry
            server = parse_server_entry(current_tokens)
            if server:
                yield server
            current_tokens = [token]
        else:
            current_tokens.append(token)

        i += 1

    # Parse final entry
    if current_tokens and len(current_tokens) >= 14:
        server = parse_server_entry(current_tokens)
        if server:
            yield server
