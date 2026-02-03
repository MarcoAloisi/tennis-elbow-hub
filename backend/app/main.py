"""FastAPI application entry point.

This module configures and creates the FastAPI application with:
- CORS middleware for cross-origin requests
- Security headers middleware
- Rate limiting
- API routes
- Health check endpoint
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.router import api_router
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging import get_logger, setup_logging
from app.core.security import get_security_headers
from app.services.scraper import get_scraper_service

# Initialize logging
setup_logging()
logger = get_logger("main")

# Initialize settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None during application lifetime.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")

    # Initialize database
    from app.core.database import init_db, close_db
    from app.services.stats_service import get_stats_service

    await init_db()
    logger.info("Database initialized")

    # Start background polling
    scraper = get_scraper_service()
    # Use configured interval or default to 60s if not set
    # Ensure interval is at least 5s for stats tracking
    interval = getattr(settings, "score_refresh_interval", 60)
    interval = max(int(interval), 5)
    
    await scraper.start_polling(interval=interval)

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop background polling
    scraper = get_scraper_service()
    await scraper.stop_polling()

    # Save any pending stats
    stats_service = get_stats_service()
    await stats_service.save_to_db()

    # Close connections
    await scraper.close()
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Live tennis score tracker and match analyzer for Tennis Elbow 4",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    # Development: allow all origins
    if settings.debug:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Add security headers to all responses.

    Args:
        request: Incoming request.
        call_next: Next middleware/handler.

    Returns:
        Response with security headers added.
    """
    response = await call_next(request)

    # Add security headers
    for header, value in get_security_headers().items():
        response.headers[header] = value

    return response


# Include API routes
app.include_router(api_router)


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Root endpoint - basic health check.

    Returns:
        Welcome message and API info.
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "version": "0.1.0",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring.

    Returns:
        Health status.
    """
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }
