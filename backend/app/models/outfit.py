from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Outfit(Base):
    """Database model for Outfit Codes."""

    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    outfit_code: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    uploader_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index('ix_outfits_title_trgm', 'title', postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'}),
    )


class OutfitRating(Base):
    """One rating (1-5) per user per outfit."""

    __tablename__ = "outfit_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outfit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("outfit_id", "user_id", name="uq_outfit_rating_user"),
    )


class OutfitBase(BaseModel):
    """Base schema for Outfit."""
    title: str
    outfit_code: str
    category: str
    uploader_name: str


class OutfitCreate(OutfitBase):
    pass


class OutfitResponse(OutfitBase):
    """Schema for returning an Outfit."""
    id: int
    image_url: str
    created_at: datetime
    avg_rating: float | None = None
    rating_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PaginatedOutfitResponse(BaseModel):
    """Paginated response for outfit listings."""
    items: list[OutfitResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RatingIn(BaseModel):
    """Request body for rating an outfit."""
    rating: int = Field(..., ge=1, le=5)
