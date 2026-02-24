"""Outfits API endpoints."""

import math
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Header, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client, create_client

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.outfit import Outfit, OutfitResponse, PaginatedOutfitResponse

router = APIRouter(prefix="/outfits", tags=["Outfits"])

# Initialize Supabase client lazily
_supabase: Client | None = None


def get_supabase() -> Client:
    """Get or initialize Supabase client."""
    global _supabase
    if _supabase is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase configuration is missing",
            )
        _supabase = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase


def get_current_user(authorization: Annotated[str, Header()]) -> Any:
    """Verify the JWT token and return the Supabase user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    
    token = authorization.split(" ")[1]
    supabase = get_supabase()
    
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return user_response.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


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
        conditions.append(Outfit.title.ilike(f"%{search}%"))
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
    current_user: Annotated[Any, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new outfit code (Authenticated users)."""
    
    # 1. Upload image to Supabase Storage
    try:
        supabase = get_supabase()
        
        # Generate unique filename
        ext = image.filename.split(".")[-1] if image.filename and "." in image.filename else "png"
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Read file content
        file_content = await image.read()
        
        # Upload
        res = supabase.storage.from_("outfits").upload(
            file=file_content,
            path=filename,
            file_options={"content-type": image.content_type or "image/png"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_("outfits").get_public_url(filename)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
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
        
    except Exception as e:
        # Note: In a robust system, we would attempt to rollback/delete the image from Supabase here
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save outfit record: {str(e)}"
        )


@router.put("/{outfit_id}", response_model=OutfitResponse)
async def update_outfit(
    outfit_id: int,
    title: Annotated[str, Form(...)],
    outfit_code: Annotated[str, Form(...)],
    category: Annotated[str, Form(...)],
    uploader_name: Annotated[str, Form(...)],
    current_user: Annotated[Any, Depends(get_current_user)],
    image: Annotated[UploadFile | None, File(...)] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing outfit (Authenticated users)."""
    
    # 1. Get outfit from DB
    result = await db.execute(select(Outfit).where(Outfit.id == outfit_id))
    outfit = result.scalar_one_or_none()
    
    if not outfit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outfit not found",
        )
        
    public_url = outfit.image_url
    
    # 2. If a new image is provided, upload it (keeping the old one in storage per spec)
    if image is not None and image.size > 0:
        try:
            supabase = get_supabase()
            
            # Generate unique filename for new image
            ext = image.filename.split(".")[-1] if image.filename and "." in image.filename else "png"
            filename = f"{uuid.uuid4()}.{ext}"
            
            file_content = await image.read()
            
            # Upload new image
            supabase.storage.from_("outfits").upload(
                file=file_content,
                path=filename,
                file_options={"content-type": image.content_type or "image/png"}
            )
            
            # Get new public URL
            public_url = supabase.storage.from_("outfits").get_public_url(filename)
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload new image: {str(e)}"
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
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update outfit record: {str(e)}"
        )


@router.delete("/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit(
    outfit_id: int,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an outfit (Authenticated users)."""
    
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
        # Extract filename from URL
        # e.g., https://xyz.supabase.co/storage/v1/object/public/outfits/uuid.png -> uuid.png
        filename = outfit.image_url.split("/")[-1]
        supabase.storage.from_("outfits").remove([filename])
    except Exception as e:
        # We'll log the error but still proceed with deleting the DB record
        print(f"Warning: Failed to delete image from Supabase: {str(e)}")
        
    # Delete DB record
    await db.delete(outfit)
    await db.commit()
