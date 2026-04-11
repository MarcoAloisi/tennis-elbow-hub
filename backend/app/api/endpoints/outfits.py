"""Outfits API endpoints."""

import math
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_supabase, require_admin
from app.core.logging import get_logger
from app.core.security import validate_image_upload
from app.core.utils import escape_like
from app.models.outfit import Outfit, OutfitResponse, PaginatedOutfitResponse

logger = get_logger("api.outfits")
router = APIRouter(prefix="/outfits", tags=["Outfits"])


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
    # Build base filter conditions
    conditions = []
    if category and category.lower() != "all":
        conditions.append(Outfit.category.ilike(category))
    if search:
        conditions.append(Outfit.title.ilike(f"%{escape_like(search)}%"))
    if uploader:
        conditions.append(Outfit.uploader_name == uploader)

    # Count total matching rows
    count_query = select(func.count(Outfit.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    total = (await db.execute(count_query)).scalar_one()

    # Fetch the page slice
    query = select(Outfit).order_by(Outfit.created_at.desc())
    for cond in conditions:
        query = query.where(cond)
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    total_pages = max(1, math.ceil(total / page_size))
    return PaginatedOutfitResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/uploaders", response_model=list[str])
async def get_uploaders(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get distinct uploader names for the author filter dropdown."""
    query = (
        select(Outfit.uploader_name)
        .distinct()
        .order_by(Outfit.uploader_name)
    )
    result = await db.execute(query)
    return result.scalars().all()


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
    
    # 1. Validate & upload image to Supabase Storage
    try:
        file_content = await validate_image_upload(image)
        supabase = get_supabase()
        
        # Generate unique filename
        ext = image.filename.split(".")[-1] if image.filename and "." in image.filename else "png"
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Upload
        supabase.storage.from_("outfits").upload(
            file=file_content,
            path=filename,
            file_options={"content-type": image.content_type or "image/png"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_("outfits").get_public_url(filename)
        
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to upload outfit image")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image. Please try again.",
        )
        
    # 2. Save metadata to Database
    try:
        db_outfit = Outfit(
            title=title,
            outfit_code=outfit_code,
            image_url=public_url,
            category=category,
            uploader_name=uploader_name,
        )
        db.add(db_outfit)
        await db.commit()
        await db.refresh(db_outfit)
        return db_outfit
        
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
    
    # 1. Get outfit from DB
    result = await db.execute(select(Outfit).where(Outfit.id == outfit_id))
    outfit = result.scalar_one_or_none()
    
    if not outfit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outfit not found",
        )
        
    public_url = outfit.image_url
    
    # 2. If a new image is provided, validate & upload it
    if image is not None and image.size and image.size > 0:
        try:
            file_content = await validate_image_upload(image)
            supabase = get_supabase()
            
            ext = image.filename.split(".")[-1] if image.filename and "." in image.filename else "png"
            filename = f"{uuid.uuid4()}.{ext}"
            
            supabase.storage.from_("outfits").upload(
                file=file_content,
                path=filename,
                file_options={"content-type": image.content_type or "image/png"}
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
            
    # 3. Update metadata in Database
    try:
        outfit.title = title
        outfit.outfit_code = outfit_code
        outfit.category = category
        outfit.uploader_name = uploader_name
        outfit.image_url = public_url
        
        await db.commit()
        await db.refresh(outfit)
        return outfit
        
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
    
    # Get outfit from DB
    result = await db.execute(select(Outfit).where(Outfit.id == outfit_id))
    outfit = result.scalar_one_or_none()
    
    if not outfit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outfit not found",
        )
        
    # Delete image from Supabase Storage
    try:
        supabase = get_supabase()
        filename = outfit.image_url.split("/")[-1]
        supabase.storage.from_("outfits").remove([filename])
    except Exception:
        logger.warning("Failed to delete outfit image from Supabase storage", exc_info=True)
        
    # Delete DB record
    await db.delete(outfit)
    await db.commit()
