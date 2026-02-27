"""Dependency injection for API endpoints."""

from typing import Annotated, Any

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client, create_client

from app.core.config import Settings, get_settings
from app.core.database import get_session_factory
from app.core.logging import get_logger
from app.services.scraper import ScraperService, get_scraper_service

logger = get_logger("api.deps")

# Type aliases for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
ScraperDep = Annotated[ScraperService, Depends(get_scraper_service)]


# ─── Supabase Client ─────────────────────────────────────────────────

_supabase: Client | None = None


def get_supabase() -> Client:
    """Get or initialize a shared Supabase client."""
    global _supabase
    if _supabase is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase configuration is missing",
            )
        _supabase = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase


# ─── Database Session ────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


# ─── Authentication & Authorization ──────────────────────────────────


def get_current_user(authorization: Annotated[str, Header()]) -> Any:
    """Verify the JWT token and return the Supabase user.

    Raises:
        HTTPException 401: If the token is missing, invalid, or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = authorization.split(" ")[1]
    supabase = get_supabase()

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return user_response.user
    except HTTPException:
        raise
    except Exception:
        logger.exception("Authentication failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


def require_admin(user: Any = Depends(get_current_user)) -> Any:
    """Require that the authenticated user has the 'admin' role.

    Uses ``app_metadata`` (``raw_app_meta_data``) which can **only** be set
    server-side via the Supabase service-role key, preventing users from
    self-escalating via the client SDK.

    Set the role in Supabase SQL Editor:
        UPDATE auth.users
        SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
        WHERE email = '...';

    Raises:
        HTTPException 403: If the user is not an admin.
    """
    app_meta = getattr(user, "app_metadata", None) or {}
    if app_meta.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
