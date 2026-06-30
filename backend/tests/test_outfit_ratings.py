"""Tests for outfit ratings model and schema."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.outfit import OutfitResponse, RatingIn


def test_rating_in_valid_range():
    for v in range(1, 6):
        assert RatingIn(rating=v).rating == v


def test_rating_in_rejects_zero():
    with pytest.raises(ValidationError):
        RatingIn(rating=0)


def test_rating_in_rejects_six():
    with pytest.raises(ValidationError):
        RatingIn(rating=6)


def test_outfit_response_rating_defaults():
    r = OutfitResponse(
        id=1,
        title="Test",
        outfit_code="code",
        category="Male",
        uploader_name="user",
        image_url="https://example.com/img.png",
        created_at=datetime.utcnow(),
    )
    assert r.avg_rating is None
    assert r.rating_count == 0


def test_outfit_response_with_rating():
    r = OutfitResponse(
        id=1,
        title="Test",
        outfit_code="code",
        category="Male",
        uploader_name="user",
        image_url="https://example.com/img.png",
        created_at=datetime.utcnow(),
        avg_rating=4.5,
        rating_count=10,
    )
    assert r.avg_rating == 4.5
    assert r.rating_count == 10
