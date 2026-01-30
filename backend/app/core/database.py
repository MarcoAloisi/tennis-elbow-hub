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
        
        _engine = create_async_engine(
            url,
            echo=get_settings().debug,
            connect_args=connect_args,
        )
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
    """Initialize database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
