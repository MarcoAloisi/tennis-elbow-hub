"""ORM models and Pydantic schemas for Tournament Predictions."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.core.database import Base


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class PredictionTournament(Base):
    __tablename__ = "prediction_tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), nullable=False, unique=True, index=True)
    managames_url: Mapped[str] = mapped_column(String(500), nullable=False)
    trn_id: Mapped[int] = mapped_column(Integer, nullable=False)
    draw_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Admin override for "Qualifier #N" → real player name. Merged with auto
    # top-down map built by the scraper. Admin entries win on conflict.
    qualifier_map: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    predictions_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    entries: Mapped[list["PredictionEntry"]] = relationship(
        "PredictionEntry", back_populates="tournament", cascade="all, delete-orphan"
    )


class PredictionEntry(Base):
    __tablename__ = "prediction_entries"
    __table_args__ = (
        UniqueConstraint("tournament_id", "ip_address", name="uq_entry_tournament_ip"),
        UniqueConstraint("tournament_id", "nickname", name="uq_entry_tournament_nickname"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("prediction_tournaments.id"), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(30), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    picks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tournament: Mapped["PredictionTournament"] = relationship("PredictionTournament", back_populates="entries")


# ─── Pydantic Schemas ───────────────────────────────────────────────────────

class TournamentCreate(BaseModel):
    managames_url: str
    predictions_close_at: datetime


class TournamentResponse(BaseModel):
    id: int
    name: str
    slug: str
    managames_url: str
    trn_id: int
    draw_data: dict
    qualifier_map: dict | None = None
    status: str
    predictions_close_at: datetime
    created_at: datetime
    updated_at: datetime
    entry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TournamentListItem(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    predictions_close_at: datetime
    created_at: datetime
    entry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class EntryCreate(BaseModel):
    nickname: str
    picks: dict  # {match_id: {winner: str, sets_count?: int, retirement?: bool}}


class EntryResponse(BaseModel):
    id: int
    tournament_id: int
    nickname: str
    picks: dict
    total_score: int
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchBreakdownItem(BaseModel):
    match_id: str
    round: str
    section: str
    predicted_winner: str | None = None
    predicted_sets: int | None = None
    predicted_retirement: bool = False
    actual_winner: str | None = None
    actual_score: str | None = None
    points: int
    reason: str


class EntryBreakdownResponse(BaseModel):
    entry_id: int
    nickname: str
    total_score: int
    items: list[MatchBreakdownItem]


class QualifierMapUpdate(BaseModel):
    mapping: dict[str, str]
