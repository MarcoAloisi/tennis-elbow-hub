"""SQLAlchemy async database configuration.

Provides async engine and session factory for PostgreSQL (production)
or SQLite (local development).
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Lazy initialization - engine created on first access
_engine = None
_session_factory = None


def get_database_url() -> str:
    """Get database URL with async driver.
    
    Returns:
        Async-compatible database URL.
    """
    settings = get_settings()
    url = settings.database_url
    
    if not url:
        # Default to SQLite for local development
        return "sqlite+aiosqlite:///./stats.db"
    
    # Convert postgres:// to postgresql+asyncpg://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return url


def get_engine():
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        url = get_database_url()
        # SQLite needs check_same_thread=False
        connect_args = {}
        if "sqlite" in url:
            connect_args["check_same_thread"] = False
        # When using Supabase transaction pooler (pgbouncer), we must disable prepared statements
        # to avoid "prepared statement already exists" errors.
        # This applies to asyncpg connections.
        elif "postgresql+asyncpg" in url:
            connect_args["statement_cache_size"] = 0
        
        engine_kwargs: dict = {
            "echo": get_settings().debug,
            "connect_args": connect_args,
        }
        # PostgreSQL supports connection pooling; SQLite does not
        if "postgresql+asyncpg" in url:
            engine_kwargs.update(
                {
                    "pool_size": 20,
                    "max_overflow": 10,
                    "pool_pre_ping": True,
                    "pool_recycle": 3600,
                }
            )

        _engine = create_async_engine(url, **engine_kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    """Initialize database tables and seed default data."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Auto-seed default video guides if the guides table is empty
    await _seed_default_guides()


async def _seed_default_guides() -> None:
    """Insert default video guides if none exist."""
    from sqlalchemy import func, select

    from app.models.guide import Guide

    session_factory = get_session_factory()
    async with session_factory() as session:
        count = (await session.execute(select(func.count(Guide.id)))).scalar_one()
        if count > 0:
            return  # Already have guides, skip seeding

        default_guides = [
            {
                "title": "How to Play Online (XKT)",
                "slug": "how-to-play-online-xkt",
                "guide_type": "video",
                "description": "Step-by-step guide to getting started with the XKT online tour.",
                "youtube_url": "https://www.youtube.com/watch?v=Zzoqi-ik568",
                "thumbnail_url": "https://img.youtube.com/vi/Zzoqi-ik568/maxresdefault.jpg",
                "tags": "XKT",
                "author_name": "Admin",
            },
            {
                "title": "How to Play Online (WTSL)",
                "slug": "how-to-play-online-wtsl",
                "guide_type": "video",
                "description": "Complete guide to joining and playing in the WTSL tour.",
                "youtube_url": "https://www.youtube.com/watch?v=9N02QlHvm54",
                "thumbnail_url": "https://img.youtube.com/vi/9N02QlHvm54/maxresdefault.jpg",
                "tags": "WTSL",
                "author_name": "Admin",
            },
            {
                "title": "Gameplay Basics Guide",
                "slug": "gameplay-basics-guide",
                "guide_type": "video",
                "description": "Learn the fundamentals of Tennis Elbow 4 gameplay.",
                "youtube_url": "https://www.youtube.com/watch?v=4naVHUvScC4",
                "thumbnail_url": "https://img.youtube.com/vi/4naVHUvScC4/maxresdefault.jpg",
                "tags": "Gameplay",
                "author_name": "Admin",
            },
        ]

        for data in default_guides:
            session.add(Guide(**data))

        await session.commit()


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
