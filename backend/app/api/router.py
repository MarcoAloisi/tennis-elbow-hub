"""Main API router that aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.endpoints import live_scores, match_analysis

# Create the main API router
api_router = APIRouter(prefix="/api")

# Include sub-routers
api_router.include_router(live_scores.router)
api_router.include_router(match_analysis.router)
