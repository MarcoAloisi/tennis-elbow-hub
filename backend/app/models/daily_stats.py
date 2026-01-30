"""Daily stats database model.

Stores aggregated match statistics per day, broken down by mod type and format.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DailyStats(Base):
    """Daily aggregated match statistics."""

    __tablename__ = "daily_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stats_date: Mapped[date] = mapped_column(Date, unique=True, index=True)

    # XKT mod stats
    xkt_total: Mapped[int] = mapped_column(Integer, default=0)
    xkt_bo1: Mapped[int] = mapped_column(Integer, default=0)
    xkt_bo3: Mapped[int] = mapped_column(Integer, default=0)
    xkt_bo5: Mapped[int] = mapped_column(Integer, default=0)

    # WTSL mod stats
    wtsl_total: Mapped[int] = mapped_column(Integer, default=0)
    wtsl_bo1: Mapped[int] = mapped_column(Integer, default=0)
    wtsl_bo3: Mapped[int] = mapped_column(Integer, default=0)
    wtsl_bo5: Mapped[int] = mapped_column(Integer, default=0)

    # Vanilla stats
    vanilla_total: Mapped[int] = mapped_column(Integer, default=0)
    vanilla_bo1: Mapped[int] = mapped_column(Integer, default=0)
    vanilla_bo3: Mapped[int] = mapped_column(Integer, default=0)
    vanilla_bo5: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "date": self.stats_date.isoformat(),
            "xkt": {
                "total": self.xkt_total,
                "bo1": self.xkt_bo1,
                "bo3": self.xkt_bo3,
                "bo5": self.xkt_bo5,
            },
            "wtsl": {
                "total": self.wtsl_total,
                "bo1": self.wtsl_bo1,
                "bo3": self.wtsl_bo3,
                "bo5": self.wtsl_bo5,
            },
            "vanilla": {
                "total": self.vanilla_total,
                "bo1": self.vanilla_bo1,
                "bo3": self.vanilla_bo3,
                "bo5": self.vanilla_bo5,
            },
        }
