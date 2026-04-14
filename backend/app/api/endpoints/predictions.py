# backend/app/api/endpoints/predictions.py
"""Tournament Predictions API endpoints."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.models.prediction import (
    EntryCreate,
    EntryResponse,
    PredictionEntry,
    PredictionTournament,
    TournamentCreate,
    TournamentListItem,
    TournamentResponse,
    _slugify,
)
from app.services.scoring import compute_entry_score
from app.services.tournament_scraper import scrape_tournament_draw

logger = get_logger("api.predictions")
router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
    """List all tournaments (active first, then by created_at desc)."""
    result = await db.execute(
        select(PredictionTournament).order_by(
            PredictionTournament.status.asc(),
            PredictionTournament.created_at.desc(),
        )
    )
    tournaments = result.scalars().all()

    out = []
    for t in tournaments:
        count_result = await db.execute(
            select(func.count(PredictionEntry.id)).where(PredictionEntry.tournament_id == t.id)
        )
        entry_count = count_result.scalar_one()
        item = TournamentListItem.model_validate(t)
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
        close_at = close_at.replace(tzinfo=timezone.utc)
    if now > close_at:
        raise HTTPException(status_code=409, detail="Prediction deadline has passed")

    nickname = body.nickname.strip()[:30]
    if not nickname:
        raise HTTPException(status_code=400, detail="Nickname is required")

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
        logger.exception("Failed to scrape tournament draw")
        raise HTTPException(status_code=422, detail=f"Failed to scrape draw: {exc}")

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
    await db.execute(
        update(PredictionTournament)
        .where(PredictionTournament.id == tournament_id)
        .values(status="closed")
    )
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
    await db.execute(
        update(PredictionTournament)
        .where(PredictionTournament.id == tournament_id)
        .values(status="finished")
    )
    await db.commit()
    return {"status": "finished"}


@router.delete("/tournaments/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
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
