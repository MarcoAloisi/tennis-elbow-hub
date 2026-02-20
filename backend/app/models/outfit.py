from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Outfit(Base):
    """Database model for Outfit Codes."""

    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    outfit_code: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    uploader_name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class OutfitBase(BaseModel):
    """Base schema for Outfit."""
    title: str
    outfit_code: str
    category: str
    uploader_name: str


class OutfitCreate(OutfitBase):
    """Schema for creating a new Outfit."""
    pass


class OutfitResponse(OutfitBase):
    """Schema for returning an Outfit."""
    id: int
    image_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
