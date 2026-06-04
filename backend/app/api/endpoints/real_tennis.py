"""Real tennis scores endpoint — proxies SofaScore via cached backend service."""

from fastapi import APIRouter, Request

from app.core.limiter import limiter
from app.services.real_tennis_service import fetch_real_tennis_scores

router = APIRouter(prefix="/real-tennis", tags=["Real Tennis"])


@router.get("/scores", summary="Get real-world tennis scores from SofaScore")
@limiter.limit("60/minute")
async def get_real_tennis_scores(request: Request) -> dict:
    """Return live + today's scheduled ATP/WTA match scores.

    Cached for 30 seconds. Returns stale cache if SofaScore is unreachable.
    """
    return await fetch_real_tennis_scores()
