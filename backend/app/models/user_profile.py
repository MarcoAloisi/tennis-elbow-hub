from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel
from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Supabase user UUID
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tours: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True, default=list)
    in_game_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    player_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # canonical player name
    player_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    favorite_tennis_player: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    favorite_tournament: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Pydantic schemas
class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    birthday: Optional[date] = None
    tours: Optional[list[str]] = None
    in_game_name: Optional[str] = None
    player_name: Optional[str] = None
    favorite_tennis_player: Optional[str] = None
    favorite_tournament: Optional[str] = None


class PlayerStatsOut(BaseModel):
    total_matches: int
    wins: int
    losses: int
    latest_elo: Optional[int]
    last_match_date: Optional[str]


class UserProfileOut(BaseModel):
    id: str
    display_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    birthday: Optional[date]
    tours: Optional[list[str]]
    in_game_name: Optional[str]
    player_name: Optional[str]
    player_verified: bool
    favorite_tennis_player: Optional[str]
    favorite_tournament: Optional[str]
    created_at: datetime
    player_stats: Optional[PlayerStatsOut] = None

    class Config:
        from_attributes = True
