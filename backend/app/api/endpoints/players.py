"""Logged-in player detail (ELO-clustered)."""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_current_user
from app.core.limiter import limiter

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/{player_name:path}")
@limiter.limit("30/minute")
async def get_player_details(
    request: Request,
    player_name: str,
    elo: int = Query(..., ge=1),
    _user: Any = Depends(get_current_user),
) -> dict:
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_player_details_async(player_name, elo=elo)
