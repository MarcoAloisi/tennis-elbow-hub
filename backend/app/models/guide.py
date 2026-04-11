"""Database model and Pydantic schemas for Guides."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class Guide(Base):
    """Database model for Guides (video or written articles)."""

    __tablename__ = "guides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(250), nullable=False, unique=True, index=True)
    guide_type: Mapped[str] = mapped_column(String(20), nullable=False, default="written", index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # HTML body for written guides
    youtube_url: Mapped[str | None] = mapped_column(String(300), nullable=True)  # For video guides
    tags: Mapped[str | None] = mapped_column(String(200), nullable=True)  # Comma-separated
    author_name: Mapped[str] = mapped_column(String(50), nullable=False, default="Admin")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# --------------- Pydantic Schemas ---------------


class GuideBase(BaseModel):
    """Base schema shared by create/update/response."""

    title: str
    guide_type: str = "written"
    description: str | None = None
    tags: str | None = None
    author_name: str = "Admin"


class GuideCreate(GuideBase):
    """Schema for creating a new Guide (used for validation docs only)."""

    content: str | None = None
    youtube_url: str | None = None


class GuideUpdate(BaseModel):
    """Schema for updating an existing Guide."""

    title: str | None = None
    guide_type: str | None = None
    description: str | None = None
    content: str | None = None
    youtube_url: str | None = None
    tags: str | None = None
    author_name: str | None = None


class GuideResponse(GuideBase):
    """Schema for returning a Guide."""

    id: int
    slug: str
    thumbnail_url: str | None = None
    content: str | None = None
    youtube_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuideListItem(BaseModel):
    """Lightweight schema for guide list cards (excludes full content)."""

    id: int
    title: str
    slug: str
    guide_type: str
    description: str | None = None
    thumbnail_url: str | None = None
    youtube_url: str | None = None
    tags: str | None = None
    author_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedGuideResponse(BaseModel):
    """Paginated response for guide listings."""

    items: list[GuideListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
