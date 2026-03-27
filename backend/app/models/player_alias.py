"""Player alias database model.

Maps alternative nicknames (aliases) to a single canonical player name.
Aliases are stored lowercase for case-insensitive matching.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlayerAlias(Base):
    """Maps an alias (nickname) to a canonical player name."""

    __tablename__ = "player_aliases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(String, unique=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
