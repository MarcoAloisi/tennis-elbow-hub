"""Dependency injection for API endpoints."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.scraper import ScraperService, get_scraper_service


# Type aliases for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
ScraperDep = Annotated[ScraperService, Depends(get_scraper_service)]
