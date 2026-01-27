"""Pydantic models for match statistics.

These models represent the parsed structure of match log HTML files,
containing detailed statistics for tennis matches.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ServeStats(BaseModel):
    """Serve-related statistics for a player."""

    first_serve_in: int = Field(ge=0, description="First serves in")
    first_serve_total: int = Field(ge=0, description="Total first serve attempts")
    first_serve_pct: float = Field(
        ge=0, le=100, description="First serve percentage"
    )
    aces: int = Field(ge=0, description="Number of aces")
    double_faults: int = Field(ge=0, description="Number of double faults")
    fastest_serve_kmh: float = Field(ge=0, description="Fastest serve speed (km/h)")
    avg_first_serve_kmh: float = Field(
        ge=0, description="Average first serve speed (km/h)"
    )
    avg_second_serve_kmh: float = Field(
        ge=0, description="Average second serve speed (km/h)"
    )


class RallyStats(BaseModel):
    """Rally-related statistics for a player."""

    short_rallies_won: int = Field(ge=0, description="Short rallies won (<5)")
    short_rallies_total: int = Field(ge=0, description="Total short rallies")
    normal_rallies_won: int = Field(ge=0, description="Normal rallies won (5-8)")
    normal_rallies_total: int = Field(ge=0, description="Total normal rallies")
    long_rallies_won: int = Field(ge=0, description="Long rallies won (>8)")
    long_rallies_total: int = Field(ge=0, description="Total long rallies")
    avg_rally_length: float = Field(ge=0, description="Average rally length")


class PointStats(BaseModel):
    """Point-related statistics for a player."""

    winners: int = Field(ge=0, description="Number of winners")
    forced_errors: int = Field(ge=0, description="Forced errors")
    unforced_errors: int = Field(ge=0, description="Unforced errors")
    net_points_won: int = Field(ge=0, description="Net points won")
    net_points_total: int = Field(ge=0, description="Total net points")
    points_on_first_serve_won: int = Field(ge=0, description="Points won on 1st serve")
    points_on_first_serve_total: int = Field(ge=0, description="Total 1st serve points")
    points_on_second_serve_won: int = Field(ge=0, description="Points won on 2nd serve")
    points_on_second_serve_total: int = Field(ge=0, description="Total 2nd serve points")
    return_points_won: int = Field(ge=0, description="Return points won")
    return_points_total: int = Field(ge=0, description="Total return points")
    return_winners: int = Field(ge=0, description="Return winners")
    total_points_won: int = Field(ge=0, description="Total points won")


class BreakPointStats(BaseModel):
    """Break point statistics for a player."""

    break_points_won: int = Field(ge=0, description="Break points converted")
    break_points_total: int = Field(ge=0, description="Total break point opportunities")
    break_games_won: int = Field(ge=0, description="Games broken")
    break_games_total: int = Field(ge=0, description="Total return games opportunity")
    set_points_saved: int = Field(ge=0, description="Set points saved")
    match_points_saved: int = Field(ge=0, description="Match points saved")


class PlayerMatchStats(BaseModel):
    """Complete match statistics for a single player."""

    name: str = Field(description="Player name")
    serve: ServeStats = Field(description="Serve statistics")
    rally: RallyStats = Field(description="Rally statistics")
    points: PointStats = Field(description="Point statistics")
    break_points: BreakPointStats = Field(description="Break point statistics")


class MatchInfo(BaseModel):
    """Basic match information from the header."""

    player1_name: str = Field(description="First player name")
    player2_name: str = Field(description="Second player name")
    score: str = Field(description="Final score")
    tournament: str = Field(description="Tournament name")
    duration: str = Field(description="Match duration")
    real_duration: str = Field(description="Real-time duration")
    date: datetime | None = Field(default=None, description="Match date")
    is_retirement: bool = Field(default=False, description="Whether the match ended in retirement")
    raw_match_id: str | None = Field(default=None, description="Unique match ID from HTML table element")



class MatchStats(BaseModel):
    """Complete match statistics for both players."""

    info: MatchInfo = Field(description="Match information")
    player1: PlayerMatchStats = Field(description="Player 1 statistics")
    player2: PlayerMatchStats = Field(description="Player 2 statistics")

    @property
    def winner(self) -> str:
        """Determine the winner.
        
        Since parsing logic ensures player1 is always the winner (from header 'Winner def. Loser'),
        we simply return player1's name.
        """
        return self.player1.name


class MatchAnalysisResponse(BaseModel):
    """Response model for match analysis endpoint."""

    success: bool = Field(description="Whether analysis was successful")
    stats: MatchStats | None = Field(default=None, description="Deprecated - use matches instead")
    matches: list[MatchStats] = Field(default_factory=list, description="List of parsed matches")
    error: str | None = Field(default=None, description="Error message if failed")
    filename: str = Field(description="Original filename")
