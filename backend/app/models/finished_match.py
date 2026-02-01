"""Finished match database model.

Stores individual finished matches to ensure robust deduplication
and precise counting even across server restarts.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FinishedMatch(Base):
    """Represents a match that has been finished and counted."""

    __tablename__ = "finished_matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    
    # Metadata for debugging/audit
    match_name: Mapped[str] = mapped_column(String)
    winner: Mapped[str | None] = mapped_column(String, nullable=True)
    score: Mapped[str | None] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
