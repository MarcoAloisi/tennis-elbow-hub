# backend/app/api/endpoints/predictions.py
"""Tournament Predictions API endpoints."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.models.prediction import (
    EntryBreakdownResponse,
    EntryCreate,
    EntryResponse,
    MatchBreakdownItem,
    PredictionEntry,
    PredictionTournament,
    QualifierMapUpdate,
    TournamentCreate,
    TournamentListItem,
    TournamentResponse,
    _slugify,
)
from app.services.scoring import compute_entry_breakdown, compute_entry_score
from app.services.tournament_scraper import (
    apply_qualifier_map,
    scrape_tournament_draw,
)

logger = get_logger("api.predictions")
router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from the TCP connection (not X-Forwarded-For).

    We use the real socket peer address to prevent header-spoofing bypass
    of the IP-lock. If a reverse proxy is in use, configure it to rewrite
    the source IP at the network level (e.g. nginx real_ip_header) rather
    than relying on X-Forwarded-For here.
    """
    return request.client.host if request.client else "unknown"


def _resolve_draw(draw_data: dict, admin_map: dict | None) -> dict:
    """Merge auto + admin qualifier maps and apply them to main-draw matches.

    The scraper stores its auto-built map at draw_data['qualifier_map_auto'].
    Admin override (tournament.qualifier_map) takes precedence. The merged
    map is stored at draw_data['qualifier_map_effective'] for frontend use.
    """
    matches = draw_data.get("matches", [])
    auto_map = draw_data.get("qualifier_map_auto") or {}
    admin = admin_map or {}
    effective: dict = {**auto_map, **admin}
    resolved_matches = apply_qualifier_map(matches, effective)
    return {
        **draw_data,
        "matches": resolved_matches,
        "qualifier_map_effective": effective,
    }


def _validate_picks(picks: dict) -> None:
    """Raise HTTPException if any pick has an invalid shape."""
    if not isinstance(picks, dict):
        raise HTTPException(status_code=400, detail="picks must be an object")
    for match_id, pick in picks.items():
        if not isinstance(pick, dict):
            raise HTTPException(status_code=400, detail=f"pick for {match_id} must be an object")
        winner = pick.get("winner", "")
        if not isinstance(winner, str):
            raise HTTPException(status_code=400, detail=f"pick.winner for {match_id} must be a string")
        if "sets_count" in pick and pick["sets_count"] is not None:
            if pick["sets_count"] not in (2, 3, 4, 5):
                raise HTTPException(status_code=400, detail=f"pick.sets_count for {match_id} must be 2-5")
        if "retirement" in pick and not isinstance(pick["retirement"], bool):
            raise HTTPException(status_code=400, detail=f"pick.retirement for {match_id} must be boolean")
        allowed = {"winner", "sets_count", "retirement"}
        extra = set(pick.keys()) - allowed
        if extra:
            raise HTTPException(status_code=400, detail=f"pick for {match_id} has unknown keys: {sorted(extra)}")


async def _unique_slug(db: AsyncSession, base: str) -> str:
    slug = base
    counter = 1
    while True:
        exists = (await db.execute(
            select(PredictionTournament).where(PredictionTournament.slug == slug)
        )).scalar_one_or_none()
        if not exists:
            return slug
        slug = f"{base}-{counter}"
        counter += 1


# ─── Public Endpoints ────────────────────────────────────────────────────────


@router.get("/tournaments", response_model=list[TournamentListItem])
@limiter.limit("60/minute")
async def list_tournaments(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all tournaments (open first, then closed, then finished; newest first)."""
    status_order = case(
        (PredictionTournament.status == "open", 0),
        (PredictionTournament.status == "closed", 1),
        else_=2,
    )
    rows = (await db.execute(
        select(PredictionTournament, func.count(PredictionEntry.id).label("entry_count"))
        .outerjoin(PredictionEntry, PredictionEntry.tournament_id == PredictionTournament.id)
        .group_by(PredictionTournament.id)
        .order_by(status_order, PredictionTournament.created_at.desc())
    )).all()

    out = []
    for tournament, entry_count in rows:
        item = TournamentListItem.model_validate(tournament)
        item.entry_count = entry_count
        out.append(item)

    return out


@router.get("/tournaments/{slug}", response_model=TournamentResponse)
@limiter.limit("60/minute")
async def get_tournament(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get tournament detail including full draw_data."""
    result = await db.execute(
        select(PredictionTournament).where(PredictionTournament.slug == slug)
    )
    tournament = result.scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    count_result = await db.execute(
        select(func.count(PredictionEntry.id)).where(PredictionEntry.tournament_id == tournament.id)
    )
    entry_count = count_result.scalar_one()

    out = TournamentResponse.model_validate(tournament)
    out.entry_count = entry_count
    return out


@router.get("/tournaments/{tournament_id}/entries", response_model=list[EntryResponse])
@limiter.limit("60/minute")
async def list_entries(
    request: Request,
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all prediction entries for a tournament, sorted by score desc."""
    tournament = (await db.execute(
        select(PredictionTournament.id).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    result = await db.execute(
        select(PredictionEntry)
        .where(PredictionEntry.tournament_id == tournament_id)
        .order_by(PredictionEntry.total_score.desc(), PredictionEntry.submitted_at.asc())
    )
    return result.scalars().all()


@router.post(
    "/tournaments/{tournament_id}/entries",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def submit_entry(
    request: Request,
    tournament_id: int,
    body: EntryCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Submit a prediction entry (anonymous, one per IP per tournament)."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if tournament.status != "open":
        raise HTTPException(status_code=409, detail="Predictions are closed for this tournament")

    now = datetime.now(timezone.utc)
    close_at = tournament.predictions_close_at
    if close_at.tzinfo is None:
        close_at = close_at.replace(tzinfo=timezone.utc)  # SQLite stores naive datetimes
    if now > close_at:
        raise HTTPException(status_code=409, detail="Prediction deadline has passed")

    nickname = body.nickname.strip()[:30]
    if not nickname:
        raise HTTPException(status_code=400, detail="Nickname is required")

    _validate_picks(body.picks)

    ip = _get_client_ip(request)

    # IP lock
    ip_exists = (await db.execute(
        select(PredictionEntry).where(
            PredictionEntry.tournament_id == tournament_id,
            PredictionEntry.ip_address == ip,
        )
    )).scalar_one_or_none()
    if ip_exists:
        raise HTTPException(status_code=409, detail="A prediction from this IP already exists")

    # Nickname lock
    nick_exists = (await db.execute(
        select(PredictionEntry).where(
            PredictionEntry.tournament_id == tournament_id,
            PredictionEntry.nickname == nickname,
        )
    )).scalar_one_or_none()
    if nick_exists:
        raise HTTPException(status_code=409, detail="This nickname is already taken for this tournament")

    entry = PredictionEntry(
        tournament_id=tournament_id,
        nickname=nickname,
        ip_address=ip,
        picks=body.picks,
        total_score=0,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


# ─── Admin Endpoints ─────────────────────────────────────────────────────────


@router.post("/tournaments", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_tournament(
    request: Request,
    body: TournamentCreate,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a tournament by scraping a managames URL (Admin only)."""
    try:
        draw_data = await scrape_tournament_draw(body.managames_url)
    except Exception as exc:
        logger.exception("Failed to scrape tournament draw — creating with empty draw")
        draw_data = {"name": "Unknown Tournament", "surface": "", "category": "",
                     "draw_size": 0, "week": "", "year": "", "matches": [],
                     "qualifier_map_auto": {}}

    draw_data = _resolve_draw(draw_data, admin_map=None)

    name = draw_data.get("name", "Unknown Tournament")
    trn_id_match = re.search(r"Trn=(\d+)", body.managames_url)
    trn_id = int(trn_id_match.group(1)) if trn_id_match else 0

    slug = await _unique_slug(db, _slugify(name))

    tournament = PredictionTournament(
        name=name,
        slug=slug,
        managames_url=body.managames_url,
        trn_id=trn_id,
        draw_data=draw_data,
        qualifier_map=None,
        status="open",
        predictions_close_at=body.predictions_close_at,
    )
    db.add(tournament)
    await db.commit()
    await db.refresh(tournament)

    out = TournamentResponse.model_validate(tournament)
    out.entry_count = 0
    return out


@router.post("/tournaments/{tournament_id}/refresh")
@limiter.limit("10/minute")
async def refresh_tournament(
    request: Request,
    tournament_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-scrape managames and recompute all entry scores (Admin only)."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    try:
        draw_data = await scrape_tournament_draw(tournament.managames_url)
    except Exception as exc:
        logger.exception("Failed to re-scrape draw")
        raise HTTPException(status_code=422, detail=f"Failed to re-scrape: {exc}")

    draw_data = _resolve_draw(draw_data, admin_map=tournament.qualifier_map)
    tournament.draw_data = draw_data
    await db.flush()

    # Recompute scores for all entries
    entries = (await db.execute(
        select(PredictionEntry).where(PredictionEntry.tournament_id == tournament_id)
    )).scalars().all()

    matches = draw_data.get("matches", [])
    for entry in entries:
        entry.total_score = compute_entry_score(entry.picks, matches)

    await db.commit()
    return {"refreshed": True, "entries_scored": len(entries)}


@router.post("/tournaments/{tournament_id}/close")
@limiter.limit("10/minute")
async def close_predictions(
    request: Request,
    tournament_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Close predictions (no new entries accepted) (Admin only)."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    tournament.status = "closed"
    await db.commit()
    return {"status": "closed"}


@router.post("/tournaments/{tournament_id}/finish")
@limiter.limit("10/minute")
async def finish_tournament(
    request: Request,
    tournament_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark tournament as finished and reveal podium (Admin only)."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    tournament.status = "finished"
    await db.commit()
    return {"status": "finished"}


@router.delete("/tournaments/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_tournament(
    request: Request,
    tournament_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tournament and all its entries (Admin only)."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    await db.delete(tournament)
    await db.commit()


@router.get(
    "/tournaments/{tournament_id}/entries/{entry_id}/breakdown",
    response_model=EntryBreakdownResponse,
)
@limiter.limit("60/minute")
async def get_entry_breakdown(
    request: Request,
    tournament_id: int,
    entry_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Per-match breakdown of an entry's picks against the actual draw."""
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    entry = (await db.execute(
        select(PredictionEntry).where(
            PredictionEntry.id == entry_id,
            PredictionEntry.tournament_id == tournament_id,
        )
    )).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    matches = (tournament.draw_data or {}).get("matches", [])
    breakdown = compute_entry_breakdown(entry.picks or {}, matches)
    items = [
        MatchBreakdownItem(
            match_id=b.match_id,
            round=b.round,
            section=b.section,
            predicted_winner=b.predicted_winner,
            predicted_sets=b.predicted_sets,
            predicted_retirement=b.predicted_retirement,
            actual_winner=b.actual_winner,
            actual_score=b.actual_score,
            points=b.points,
            reason=b.reason,
        )
        for b in breakdown
    ]
    return EntryBreakdownResponse(
        entry_id=entry.id,
        nickname=entry.nickname,
        total_score=entry.total_score,
        items=items,
    )


@router.put("/tournaments/{tournament_id}/qualifier-map")
@limiter.limit("10/minute")
async def update_qualifier_map(
    request: Request,
    tournament_id: int,
    body: QualifierMapUpdate,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set the admin qualifier override map (Admin only).

    Does not re-scrape. Call /refresh afterwards to apply to the draw and
    recompute entry scores.
    """
    tournament = (await db.execute(
        select(PredictionTournament).where(PredictionTournament.id == tournament_id)
    )).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    cleaned: dict[str, str] = {}
    for key, val in (body.mapping or {}).items():
        if not isinstance(key, str) or not isinstance(val, str):
            continue
        k = key.strip()
        v = val.strip()
        if not k or not v:
            continue
        cleaned[k] = v

    tournament.qualifier_map = cleaned or None
    # Re-apply to cached draw_data so the change is immediately visible
    # (scores are only recomputed on explicit /refresh).
    if tournament.draw_data:
        tournament.draw_data = _resolve_draw(tournament.draw_data, admin_map=tournament.qualifier_map)
    await db.commit()
    return {"qualifier_map": tournament.qualifier_map or {}}


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_entry(
    request: Request,
    entry_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a suspicious or duplicate entry (Admin only)."""
    entry = (await db.execute(
        select(PredictionEntry).where(PredictionEntry.id == entry_id)
    )).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)
    await db.commit()
