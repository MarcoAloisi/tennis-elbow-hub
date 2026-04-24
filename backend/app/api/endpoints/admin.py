"""Admin-only API endpoints.

Provides endpoints for admin-only features, protected by the require_admin dependency.
"""

import csv
import io
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, select

from app.api.deps import get_db, require_admin
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.models.player_alias import PlayerAlias
from app.models.user_profile import UserProfile

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

    Returns the full list — the admin view handles filtering and sorting client-side.
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
    """Download all players as a CSV file."""
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    players = await stats_service.get_all_players_async()

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


@router.get(
    "/players/{player_name:path}",
    summary="Get detailed player stats",
    description="Get detailed match history, W/L record, best win, worst loss, and activity for a player. Admin only.",
)
@limiter.limit("30/minute")
async def get_player_details(
    request: Request,
    player_name: str,
    _admin=Depends(require_admin),
) -> dict:
    """Get detailed stats for a specific player."""
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    return await stats_service.get_player_details_async(player_name)


# ─── Nickname / Alias Mapping ───────────────────────────────────────


class AliasMappingRequest(BaseModel):
    """Request body for creating alias mappings."""
    canonical_name: str
    aliases: list[str]


@router.get(
    "/aliases",
    summary="List all alias mappings",
    description="Get all nickname-to-canonical-name mappings. Admin only.",
)
@limiter.limit("30/minute")
async def list_aliases(
    request: Request,
    _admin=Depends(require_admin),
    db=Depends(get_db),
) -> list[dict]:
    """Return all alias mappings."""
    result = await db.execute(
        select(PlayerAlias).order_by(PlayerAlias.canonical_name, PlayerAlias.alias)
    )
    aliases = result.scalars().all()
    return [
        {
            "id": a.id,
            "alias": a.alias,
            "canonical_name": a.canonical_name,
        }
        for a in aliases
    ]


@router.post(
    "/aliases",
    summary="Create alias mappings",
    description="Map one or more nicknames to a canonical player name. Admin only.",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_aliases(
    request: Request,
    body: AliasMappingRequest,
    _admin=Depends(require_admin),
    db=Depends(get_db),
) -> dict:
    """Create alias mappings for a canonical name."""
    canonical = body.canonical_name.strip()
    if not canonical:
        raise HTTPException(status_code=400, detail="canonical_name is required")

    created = []
    skipped = []

    for raw_alias in body.aliases:
        alias_lower = raw_alias.strip().lower()
        if not alias_lower or alias_lower == canonical.lower():
            continue

        # Check if alias already exists
        exists = await db.execute(
            select(PlayerAlias).where(PlayerAlias.alias == alias_lower)
        )
        if exists.scalar_one_or_none():
            skipped.append(alias_lower)
            continue

        db.add(PlayerAlias(alias=alias_lower, canonical_name=canonical))
        created.append(alias_lower)

    await db.commit()
    return {"created": created, "skipped": skipped}


@router.delete(
    "/aliases/{alias}",
    summary="Delete an alias mapping",
    description="Remove a single nickname mapping. Admin only.",
)
@limiter.limit("30/minute")
async def delete_alias(
    request: Request,
    alias: str,
    _admin=Depends(require_admin),
    db=Depends(get_db),
) -> dict:
    """Delete a single alias mapping."""
    alias_lower = alias.strip().lower()
    result = await db.execute(
        delete(PlayerAlias).where(PlayerAlias.alias == alias_lower)
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alias not found")

    return {"deleted": alias_lower}


class RenameRequest(BaseModel):
    """Request body for renaming a canonical player name."""
    old_name: str
    new_name: str


@router.put(
    "/aliases/rename",
    summary="Rename a canonical player name",
    description="Rename a player: updates all aliases to point to the new name and adds the old name as an alias. Admin only.",
)
@limiter.limit("30/minute")
async def rename_canonical(
    request: Request,
    body: RenameRequest,
    _admin=Depends(require_admin),
    db=Depends(get_db),
) -> dict:
    """Rename a canonical name and add the old name as alias."""
    old_name = body.old_name.strip()
    new_name = body.new_name.strip()

    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="Both old_name and new_name are required")
    if old_name.lower() == new_name.lower():
        raise HTTPException(status_code=400, detail="Names are the same")

    # Update all aliases that pointed to old_name → now point to new_name
    from sqlalchemy import update
    result = await db.execute(
        update(PlayerAlias)
        .where(PlayerAlias.canonical_name == old_name)
        .values(canonical_name=new_name)
    )
    updated_count = result.rowcount

    # Add old_name as an alias of new_name (if not already mapped)
    old_name_lower = old_name.lower()
    exists = await db.execute(
        select(PlayerAlias).where(PlayerAlias.alias == old_name_lower)
    )
    if not exists.scalar_one_or_none():
        db.add(PlayerAlias(alias=old_name_lower, canonical_name=new_name))

    # If new_name was previously an alias of old_name, remove that to avoid circular reference
    new_name_lower = new_name.lower()
    await db.execute(
        delete(PlayerAlias).where(PlayerAlias.alias == new_name_lower)
    )

    await db.commit()
    return {"old_name": old_name, "new_name": new_name, "aliases_updated": updated_count}


# ─── Profile Verification ───────────────────────────────────────


@router.get("/profile-verifications")
@limiter.limit("60/minute")
async def list_pending_verifications(
    request: Request,
    _admin: Any = Depends(require_admin),
    db=Depends(get_db),
):
    """List user profiles pending player name verification."""
    result = await db.execute(
        select(UserProfile).where(
            UserProfile.player_name.isnot(None),
            UserProfile.player_verified == False,  # noqa: E712
        )
    )
    profiles = result.scalars().all()
    return [
        {
            "user_id": p.id,
            "display_name": p.display_name,
            "in_game_name": p.in_game_name,
            "player_name": p.player_name,
            "created_at": p.created_at,
        }
        for p in profiles
    ]


@router.post("/profile-verifications/{user_id}/approve")
@limiter.limit("60/minute")
async def approve_player_link(
    request: Request,
    user_id: str,
    _admin: Any = Depends(require_admin),
    db=Depends(get_db),
):
    """Approve a user's player name link."""
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.player_verified = True
    await db.commit()
    return {"approved": True, "player_name": profile.player_name}


@router.post("/profile-verifications/{user_id}/reject")
@limiter.limit("60/minute")
async def reject_player_link(
    request: Request,
    user_id: str,
    _admin: Any = Depends(require_admin),
    db=Depends(get_db),
):
    """Reject a user's player name link."""
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.player_name = None
    profile.player_verified = False
    await db.commit()
    return {"rejected": True}

