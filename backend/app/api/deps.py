"""Dependency injection for API endpoints."""

from typing import Annotated

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session_factory
from app.services.scraper import ScraperService, get_scraper_service


# Type aliases for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
ScraperDep = Annotated[ScraperService, Depends(get_scraper_service)]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
