"""Game-by-game history of a live match."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatchGameEvent(Base):
    """A completed game within a match."""

    __tablename__ = "match_game_events"

    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    set_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    p1_games: Mapped[int] = mapped_column(Integer)
    p2_games: Mapped[int] = mapped_column(Integer)
    winner: Mapped[int] = mapped_column(Integer)
    server: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_tiebreak: Mapped[bool] = mapped_column(Boolean, default=False)
    points: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


class GameEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    set_number: int
    game_number: int
    p1_games: int
    p2_games: int
    winner: Literal[1, 2]
    server: Literal[1, 2] | None
    is_tiebreak: bool
    points: list[str] | None
