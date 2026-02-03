"""Pydantic models for game server data.

These models represent the parsed structure of Tennis Elbow 4 server data,
including the GameInfo bitfield and complete server entries.
"""

from enum import IntEnum

from pydantic import BaseModel, Field, computed_field


class PlayerConfig(IntEnum):
    """Game mode configuration from GameInfo bitfield."""

    SINGLES = 0
    UNKNOWN_1 = 1
    COMPETITIVE_DOUBLES = 2
    COOPERATIVE_DOUBLES = 3


class SkillMode(IntEnum):
    """Skill mode from GameInfo bitfield."""

    BEGINNER = 0
    INTERMEDIATE = 1
    ADVANCED = 2
    EXPERT = 3


class ControlMode(IntEnum):
    """Control mode from GameInfo bitfield."""

    KEYBOARD = 0
    MOUSE = 1
    GAMEPAD = 2
    MIXED = 3


class GameInfo(BaseModel):
    """Parsed GameInfo bitfield from server data.

    Bitfield layout (28 bits total):
    - Bits 0-1: Trial (2 bits)
    - Bits 2-4: PlayerCfg (3 bits) - game mode
    - Bits 5-6: NbSet (2 bits) - number of sets
    - Bits 7-8: SkillMode (2 bits)
    - Bits 9-17: Empty/reserved (9 bits)
    - Bits 18-20: GamePerSet (3 bits)
    - Bit 21: Unused (1 bit)
    - Bits 22-23: ControlMode (2 bits)
    - Bits 24-26: Preview (3 bits)
    - Bit 27: Tiredness (1 bit)
    """

    trial: int = Field(ge=0, le=3, description="Trial flag (2 bits)")
    player_config: PlayerConfig = Field(description="Game mode configuration")
    nb_set: int = Field(ge=0, le=3, description="Number of sets configuration")
    skill_mode: SkillMode = Field(description="Skill mode")
    games_per_set: int = Field(ge=0, le=7, description="Games per set")
    control_mode: ControlMode = Field(description="Control mode")
    preview: int = Field(ge=0, le=7, description="Preview setting")
    tiredness: bool = Field(description="Tiredness enabled")

    @computed_field
    @property
    def mode_display(self) -> str:
        """Human-readable game mode."""
        mode_names = {
            PlayerConfig.SINGLES: "Singles",
            PlayerConfig.COMPETITIVE_DOUBLES: "Competitive Doubles",
            PlayerConfig.COOPERATIVE_DOUBLES: "Cooperative Doubles",
        }
        return mode_names.get(self.player_config, "Unknown")

    @computed_field
    @property
    def sets_display(self) -> str:
        """Human-readable number of sets.

        NbSet encoding from GameInfo bitfield (2 bits):
        The value represents the number of sets to play:
        - 0: Best of 1 (single set match)
        - 1: Best of 1 (single set)
        - 2: Best of 3 (first to 2 sets)
        - 3: Best of 5 (first to 3 sets)
        """
        set_map = {0: "Best of 1", 1: "Best of 1", 2: "Best of 3", 3: "Best of 5"}
        return set_map.get(self.nb_set, f"Best of {self.nb_set}")


class GameServer(BaseModel):
    """Represents a live tennis match server.

    Format from source:
    IP Port "Name" GameInfo MaxPing Elo NbGame "TagLine" "Score" OtherElo
    GiveUpRate Reputation "SurfaceName" CreationTimeInMs
    """

    ip: str = Field(description="Server IP address (0 if match started)")
    port: int = Field(ge=0, description="Server port")
    match_name: str = Field(description="Match name (e.g., 'Player1 vs Player2')")
    game_info: GameInfo = Field(description="Parsed game configuration")
    max_ping: int = Field(ge=0, description="Maximum ping in milliseconds")
    elo: int = Field(ge=0, description="Primary player Elo rating")
    nb_game: int = Field(ge=0, description="Number of games played")
    tag_line: str = Field(description="Server tag line or version info")
    score: str = Field(description="Current match score")
    other_elo: int = Field(description="Other player Elo rating")
    give_up_rate: int = Field(description="Give up rate statistic")
    reputation: int = Field(description="Server/player reputation")
    surface_name: str = Field(description="Court surface name")
    creation_time_ms: int = Field(ge=0, description="Server creation timestamp")
    is_started: bool = Field(description="True if match has started (IP=0)")

    @computed_field
    @property
    def player_names(self) -> tuple[str, str]:
        """Extract player names from match_name."""
        if " vs " in self.match_name:
            parts = self.match_name.split(" vs ", 1)
            return (parts[0].strip(), parts[1].strip())
        return (self.match_name, "Unknown")

    @computed_field
    @property
    def match_id(self) -> str:
        """Generate a unique match identifier.
        
        Combines creation_time_ms with match_name and port to create
        a stable unique ID for tracking purposes.
        """
        import hashlib
        
        # Combine key identifying fields
        raw = f"{self.creation_time_ms}:{self.match_name}:{self.port}"
        # Create a stable ID using SHA256 (truncated to 16 chars)
        hash_hex = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"m_{hash_hex}"

    @computed_field
    @property
    def surface_display(self) -> str:
        """Clean surface name for display.

        The surface_name field may contain:
        - Actual surface types: "BlueGreenCement", "Clay", "Grass", "Indoor"
        - Tournament names with codes: "0010 AO Rod Laver Night"
        """
        import re

        name = self.surface_name.strip()

        # Map known surface codes to display names
        surface_map = {
            "BlueGreenCement": "Hard Court",
            "Clay": "Clay Court",
            "Grass": "Grass Court",
            "Indoor": "Indoor Hard",
            "Carpet": "Carpet",
        }

        # Check if it's a known surface type
        if name in surface_map:
            return surface_map[name]

        # Check if surface type is embedded in the name
        name_lower = name.lower()
        if "clay" in name_lower:
            return "Clay Court"
        if "grass" in name_lower:
            return "Grass Court"
        if "indoor" in name_lower:
            return "Indoor Hard"
        if "cement" in name_lower or "hard" in name_lower:
            return "Hard Court"

        # For tournament names (like "0010 AO Rod Laver Night"), return generic
        # based on tournament context
        if re.match(r"^\d+\s+", name):
            # Has numeric prefix - it's a tournament name, try to infer surface
            if "AO" in name or "Australian" in name:
                return "Hard Court"  # Australian Open is hard court
            if "Wimbledon" in name:
                return "Grass Court"
            if "Roland Garros" in name or "French" in name or "Roma" in name:
                return "Clay Court"
            if "US Open" in name:
                return "Hard Court"
            # Default for tournaments
            return "Hard Court"

        return name

    @computed_field
    @property
    def tournament_display(self) -> str:
        """Extract tournament name for display.

        Cleans up tournament names by removing numeric prefix codes.
        E.g., "0010 AO Rod Laver Night" -> "AO Rod Laver Night"
        """
        import re

        name = self.surface_name.strip()

        # Known surface types are not tournament names
        known_surfaces = {"BlueGreenCement", "Clay", "Grass", "Indoor", "Carpet"}
        if name in known_surfaces:
            return ""

        # Remove numeric prefix (e.g., "0010 " or "00031 ")
        cleaned = re.sub(r"^\d+\s+", "", name)

        # If the name is just a surface type after cleaning, return empty
        if cleaned in known_surfaces:
            return ""

        return cleaned if cleaned != name else name


class GameServerList(BaseModel):
    """Response model for list of game servers."""

    servers: list[GameServer] = Field(default_factory=list)
    total: int = Field(ge=0, description="Total number of servers")
    timestamp: str = Field(description="ISO timestamp of data fetch")
