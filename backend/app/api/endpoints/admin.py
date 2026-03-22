"""Admin-only API endpoints.

Provides endpoints for admin-only features, protected by the require_admin dependency.
"""

import csv
import io
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import require_admin
from app.core.limiter import limiter
from app.core.logging import get_logger

logger = get_logger("api.admin")
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/players",
    summary="Get all players database",
    description="Get all players with their latest ELO, total matches, and last match date. Admin only.",
)
@limiter.limit("30/minute")
async def get_all_players(
    request: Request,
    _admin=Depends(require_admin),
) -> list[dict]:
    """Get all players for admin database view.

    Returns:
        List of all players with stats.
    """
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_all_players_async()


@router.get(
    "/players/csv",
    summary="Download players database as CSV",
    description="Download all players data as a CSV file. Admin only.",
)
@limiter.limit("10/minute")
async def get_all_players_csv(
    request: Request,
    _admin=Depends(require_admin),
) -> StreamingResponse:
    """Download all players as a CSV file.

    Returns:
        StreamingResponse with CSV content.
    """
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    players = await stats_service.get_all_players_async()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Player Name", "Latest ELO", "Total Matches", "Last Match Date"])

    for player in players:
        writer.writerow([
            player["name"],
            player.get("latest_elo", ""),
            player.get("total_matches", 0),
            player.get("last_match_date", ""),
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=players_database.csv"},
    )
