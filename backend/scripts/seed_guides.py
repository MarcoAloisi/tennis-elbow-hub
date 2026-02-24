"""Seed script to migrate existing video guides from guides.json into the database.

Run this once after deploying the new guides feature:
    python -m backend.scripts.seed_guides

Or from the backend directory:
    python scripts/seed_guides.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import get_session_factory, init_db
from app.models.guide import Guide, _slugify


SEED_GUIDES = [
    {
        "title": "How to Play Online (XKT)",
        "guide_type": "video",
        "description": "Step-by-step guide to getting started with the XKT online tour.",
        "youtube_url": "https://www.youtube.com/watch?v=Zzoqi-ik568",
        "thumbnail_url": "https://img.youtube.com/vi/Zzoqi-ik568/maxresdefault.jpg",
        "tags": "XKT",
        "author_name": "Admin",
    },
    {
        "title": "How to Play Online (WTSL)",
        "guide_type": "video",
        "description": "Complete guide to joining and playing in the WTSL tour.",
        "youtube_url": "https://www.youtube.com/watch?v=9N02QlHvm54",
        "thumbnail_url": "https://img.youtube.com/vi/9N02QlHvm54/maxresdefault.jpg",
        "tags": "WTSL",
        "author_name": "Admin",
    },
    {
        "title": "Gameplay Basics Guide",
        "guide_type": "video",
        "description": "Learn the fundamentals of Tennis Elbow 4 gameplay.",
        "youtube_url": "https://www.youtube.com/watch?v=4naVHUvScC4",
        "thumbnail_url": "https://img.youtube.com/vi/4naVHUvScC4/maxresdefault.jpg",
        "tags": "Gameplay",
        "author_name": "Admin",
    },
]


async def seed() -> None:
    """Insert seed guides if they don't already exist."""
    await init_db()
    session_factory = get_session_factory()

    async with session_factory() as session:
        for guide_data in SEED_GUIDES:
            slug = _slugify(guide_data["title"])

            # Check if already seeded
            from sqlalchemy import select
            result = await session.execute(
                select(Guide).where(Guide.slug == slug)
            )
            if result.scalar_one_or_none() is not None:
                print(f"  ⏭️  Skipping (already exists): {guide_data['title']}")
                continue

            guide = Guide(slug=slug, **guide_data)
            session.add(guide)
            print(f"  ✅  Seeded: {guide_data['title']}")

        await session.commit()
        print("\n🎉 Seed complete!")


if __name__ == "__main__":
    print("🌱 Seeding video guides...\n")
    asyncio.run(seed())
