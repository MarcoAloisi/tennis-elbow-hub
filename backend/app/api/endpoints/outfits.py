"""Outfits API endpoints."""

import math
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_supabase, require_admin
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.security import validate_image_upload
from app.core.utils import escape_like
from app.models.outfit import Outfit, OutfitRating, OutfitResponse, PaginatedOutfitResponse, RatingIn

logger = get_logger("api.outfits")
router = APIRouter(prefix="/outfits", tags=["Outfits"])


def _rating_subquery():
    """Subquery: avg_rating and rating_count grouped by outfit_id."""
    return (
        select(
            OutfitRating.outfit_id,
            func.avg(OutfitRating.rating).label("avg_rating"),
            func.count(OutfitRating.id).label("rating_count"),
        )
        .group_by(OutfitRating.outfit_id)
        .subquery()
    )


def _build_response(outfit: Outfit, avg: Any, cnt: Any) -> OutfitResponse:
    item = OutfitResponse.model_validate(outfit)
    item.avg_rating = float(avg) if avg is not None else None
    item.rating_count = int(cnt) if cnt else 0
    return item


@router.get("", response_model=PaginatedOutfitResponse)
async def get_outfits(
    db: AsyncSession = Depends(get_db),
    category: str | None = None,
    search: str | None = None,
    uploader: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
) -> Any:
    """Get outfits with search, filter, and pagination."""
    conditions = []
    if category and category.lower() != "all":
        conditions.append(Outfit.category.ilike(category))
    if search:
        conditions.append(Outfit.title.ilike(f"%{escape_like(search)}%"))
    if uploader:
        conditions.append(Outfit.uploader_name == uploader)

    count_query = select(func.count(Outfit.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    total = (await db.execute(count_query)).scalar_one()

    rsq = _rating_subquery()
    query = (
        select(Outfit, rsq.c.avg_rating, rsq.c.rating_count)
        .outerjoin(rsq, Outfit.id == rsq.c.outfit_id)
        .order_by(Outfit.created_at.desc())
    )
    for cond in conditions:
        query = query.where(cond)
    query = query.offset((page - 1) * page_size).limit(page_size)

    rows = (await db.execute(query)).all()
    items = [_build_response(o, avg, cnt) for o, avg, cnt in rows]

    return PaginatedOutfitResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/uploaders", response_model=list[str])
async def get_uploaders(db: AsyncSession = Depends(get_db)) -> Any:
    """Get distinct uploader names for the author filter dropdown."""
    result = await db.execute(
        select(Outfit.uploader_name).distinct().order_by(Outfit.uploader_name)
    )
    return result.scalars().all()


# /my-ratings MUST be declared before /{outfit_id} routes
@router.get("/my-ratings", response_model=dict[int, int])
@limiter.limit("60/minute")
async def get_my_ratings(
    request: Request,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return {outfit_id: rating} for all outfits the current user has rated."""
    result = await db.execute(
        select(OutfitRating.outfit_id, OutfitRating.rating)
        .where(OutfitRating.user_id == current_user.id)
    )
    return {row.outfit_id: row.rating for row in result.all()}


@router.post("/{outfit_id}/rate", response_model=OutfitResponse)
@limiter.limit("30/minute")
async def rate_outfit(
    request: Request,
    outfit_id: int,
    body: RatingIn,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Upsert a 1-5 star rating. Auth required."""
    outfit = (await db.execute(select(Outfit).where(Outfit.id == outfit_id))).scalar_one_or_none()
    if not outfit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    existing = (await db.execute(
        select(OutfitRating).where(
            OutfitRating.outfit_id == outfit_id,
            OutfitRating.user_id == current_user.id,
        )
    )).scalar_one_or_none()

    if existing:
        existing.rating = body.rating
    else:
        db.add(OutfitRating(outfit_id=outfit_id, user_id=current_user.id, rating=body.rating))
    await db.commit()

    avg_row = (await db.execute(
        select(func.avg(OutfitRating.rating), func.count(OutfitRating.id))
        .where(OutfitRating.outfit_id == outfit_id)
    )).one()
    return _build_response(outfit, avg_row[0], avg_row[1])


@router.post("", response_model=OutfitResponse, status_code=status.HTTP_201_CREATED)
async def create_outfit(
    title: Annotated[str, Form(...)],
    outfit_code: Annotated[str, Form(...)],
    category: Annotated[str, Form(...)],
    uploader_name: Annotated[str, Form(...)],
    image: Annotated[UploadFile, File(...)],
    current_user: Annotated[Any, Depends(require_admin)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new outfit code (Admin only)."""
    try:
        file_content = await validate_image_upload(image)
        supabase = get_supabase()
        ext = image.filename.split(".")[-1] if image.filename and "." in image.filename else "png"
        filename = f"{uuid.uuid4()}.{ext}"
        supabase.storage.from_("outfits").upload(
            file=file_content,
            path=filename,
            file_options={
                "content-type": image.content_type or "image/png",
                "cache-control": "31536000",
            }
        )
        public_url = supabase.storage.from_("outfits").get_public_url(filename)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to upload outfit image")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image. Please try again.",
        )

    try:
        db_outfit = Outfit(
            title=title, outfit_code=outfit_code, image_url=public_url,
            category=category, uploader_name=uploader_name,
        )
        db.add(db_outfit)
        await db.commit()
        await db.refresh(db_outfit)
        return _build_response(db_outfit, None, 0)
    except Exception:
        await db.rollback()
        logger.exception("Failed to save outfit record")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save outfit. Please try again.",
        )


@router.put("/{outfit_id}", response_model=OutfitResponse)
async def update_outfit(
    outfit_id: int,
    title: Annotated[str, Form(...)],
    outfit_code: Annotated[str, Form(...)],
    category: Annotated[str, Form(...)],
    uploader_name: Annotated[str, Form(...)],
    current_user: Annotated[Any, Depends(require_admin)],
    image: Annotated[UploadFile | None, File(...)] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing outfit (Admin only)."""
    result = await db.execute(select(Outfit).where(Outfit.id == outfit_id))
    outfit = result.scalar_one_or_none()
    if not outfit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    public_url = outfit.image_url
    if image is not None and image.size and image.size > 0:
        try:
            file_content = await validate_image_upload(image)
            supabase = get_supabase()
            ext = image.filename.split(".")[-1] if image.filename and "." in image.filename else "png"
            filename = f"{uuid.uuid4()}.{ext}"
            supabase.storage.from_("outfits").upload(
                file=file_content, path=filename,
                file_options={
                    "content-type": image.content_type or "image/png",
                    "cache-control": "31536000",
                }
            )
            public_url = supabase.storage.from_("outfits").get_public_url(filename)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to upload new outfit image")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image. Please try again.",
            )

    try:
        outfit.title = title
        outfit.outfit_code = outfit_code
        outfit.category = category
        outfit.uploader_name = uploader_name
        outfit.image_url = public_url
        await db.commit()
        await db.refresh(outfit)
        avg_row = (await db.execute(
            select(func.avg(OutfitRating.rating), func.count(OutfitRating.id))
            .where(OutfitRating.outfit_id == outfit_id)
        )).one()
        return _build_response(outfit, avg_row[0], avg_row[1])
    except Exception:
        await db.rollback()
        logger.exception("Failed to update outfit record")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update outfit. Please try again.",
        )


@router.delete("/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit(
    outfit_id: int,
    current_user: Annotated[Any, Depends(require_admin)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an outfit (Admin only)."""
    result = await db.execute(select(Outfit).where(Outfit.id == outfit_id))
    outfit = result.scalar_one_or_none()
    if not outfit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    try:
        supabase = get_supabase()
        filename = outfit.image_url.split("/")[-1]
        supabase.storage.from_("outfits").remove([filename])
    except Exception:
        logger.warning("Failed to delete outfit image from Supabase storage", exc_info=True)

    await db.delete(outfit)
    await db.commit()
