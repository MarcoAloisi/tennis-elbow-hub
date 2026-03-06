"""Guides API endpoints."""

import math
import re
import uuid
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_supabase, require_admin
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import validate_image_upload
from app.models.guide import (
    Guide,
    GuideListItem,
    GuideResponse,
    PaginatedGuideResponse,
    _slugify,
)

logger = get_logger("api.guides")
router = APIRouter(prefix="/guides", tags=["Guides"])

BUCKET_NAME = "guide-thumbnails"
IMAGE_BUCKET_NAME = "guide-images"


def _escape_like(value: str) -> str:
    """Escape special LIKE/ILIKE pattern characters."""
    return value.replace("%", r"\%").replace("_", r"\_")


async def _generate_unique_slug(db: AsyncSession, title: str, exclude_id: int | None = None) -> str:
    """Generate a unique slug from the title, appending a counter if needed."""
    base_slug = _slugify(title)
    slug = base_slug
    counter = 1

    while True:
        query = select(Guide).where(Guide.slug == slug)
        if exclude_id is not None:
            query = query.where(Guide.id != exclude_id)
        result = await db.execute(query)
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


# ─── Image Upload Endpoint ───────────────────────────────────────────


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_guide_image(
    image: Annotated[UploadFile, File(...)],
    current_user: Annotated[Any, Depends(require_admin)],
) -> dict[str, str]:
    """Upload an image for use in guide content (Admin only).

    Validates the file and stores it in the ``guide-images`` Supabase
    bucket.  Returns the public URL so the frontend can insert it into
    the TipTap editor.
    """
    try:
        file_content = await validate_image_upload(image)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Image validation failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file.",
        )

    ext = (
        image.filename.split(".")[-1]
        if image.filename and "." in image.filename
        else "png"
    )
    filename = f"{uuid.uuid4()}.{ext}"

    try:
        supabase = get_supabase()
        supabase.storage.from_(IMAGE_BUCKET_NAME).upload(
            file=file_content,
            path=filename,
            file_options={"content-type": image.content_type or "image/png"},
        )
        url = supabase.storage.from_(IMAGE_BUCKET_NAME).get_public_url(filename)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to upload guide image to storage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image. Please try again.",
        )

    return {"url": url}


# ─── Public Endpoints ────────────────────────────────────────────────


@router.get("", response_model=PaginatedGuideResponse)
async def get_guides(
    db: AsyncSession = Depends(get_db),
    tag: str | None = None,
    guide_type: str | None = Query(None, alias="type"),
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
) -> Any:
    """List guides with optional tag, type, and search filters plus pagination."""
    conditions = []

    if tag and tag.lower() != "all":
        conditions.append(Guide.tags.ilike(f"%{_escape_like(tag)}%"))
    if guide_type:
        conditions.append(Guide.guide_type == guide_type)
    if search:
        conditions.append(Guide.title.ilike(f"%{_escape_like(search)}%"))

    # Total count
    count_query = select(func.count(Guide.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page slice
    query = select(Guide).order_by(Guide.created_at.desc())
    for cond in conditions:
        query = query.where(cond)
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    total_pages = max(1, math.ceil(total / page_size))
    return PaginatedGuideResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/tags", response_model=list[str])
async def get_tags(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get distinct tags across all guides."""
    query = select(Guide.tags).where(Guide.tags.isnot(None)).where(Guide.tags != "")
    result = await db.execute(query)
    raw_tags = result.scalars().all()

    # Split comma-separated tags, deduplicate, and sort
    tag_set: set[str] = set()
    for raw in raw_tags:
        for tag in raw.split(","):
            tag = tag.strip()
            if tag:
                tag_set.add(tag)

    return sorted(tag_set)


@router.get("/{slug}", response_model=GuideResponse)
async def get_guide_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a single guide by slug."""
    result = await db.execute(select(Guide).where(Guide.slug == slug))
    guide = result.scalar_one_or_none()

    if not guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guide not found",
        )
    return guide


# ─── Authenticated Endpoints ─────────────────────────────────────────


@router.post("", response_model=GuideResponse, status_code=status.HTTP_201_CREATED)
async def create_guide(
    title: Annotated[str, Form(...)],
    guide_type: Annotated[str, Form(...)],
    author_name: Annotated[str, Form(...)],
    current_user: Annotated[Any, Depends(require_admin)],
    description: str = Form(default=""),
    tags: str = Form(default=""),
    content: str = Form(default=""),
    youtube_url: str = Form(default=""),
    thumbnail: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new guide (Admin only)."""
    thumbnail_url: str | None = None

    # Upload thumbnail to Supabase Storage if provided
    if thumbnail is not None and thumbnail.size and thumbnail.size > 0:
        try:
            file_content = await validate_image_upload(thumbnail)
            supabase = get_supabase()
            ext = thumbnail.filename.split(".")[-1] if thumbnail.filename and "." in thumbnail.filename else "png"
            filename = f"{uuid.uuid4()}.{ext}"

            supabase.storage.from_(BUCKET_NAME).upload(
                file=file_content,
                path=filename,
                file_options={"content-type": thumbnail.content_type or "image/png"},
            )
            thumbnail_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to upload guide thumbnail")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload thumbnail. Please try again.",
            )

    # For video guides without a custom thumbnail, auto-generate from YouTube
    if not thumbnail_url and guide_type == "video" and youtube_url:
        video_id = _extract_youtube_id(youtube_url)
        if video_id:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    slug = await _generate_unique_slug(db, title)

    try:
        db_guide = Guide(
            title=title,
            slug=slug,
            guide_type=guide_type,
            description=description or None,
            thumbnail_url=thumbnail_url,
            content=content or None,
            youtube_url=youtube_url or None,
            tags=tags or None,
            author_name=author_name,
        )
        db.add(db_guide)
        await db.commit()
        await db.refresh(db_guide)
        return db_guide
    except Exception:
        await db.rollback()
        logger.exception("Failed to save guide")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save guide. Please try again.",
        )


@router.put("/{guide_id}", response_model=GuideResponse)
async def update_guide(
    guide_id: int,
    title: Annotated[str, Form(...)],
    guide_type: Annotated[str, Form(...)],
    author_name: Annotated[str, Form(...)],
    current_user: Annotated[Any, Depends(require_admin)],
    description: str = Form(default=""),
    tags: str = Form(default=""),
    content: str = Form(default=""),
    youtube_url: str = Form(default=""),
    thumbnail: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing guide (Admin only)."""
    result = await db.execute(select(Guide).where(Guide.id == guide_id))
    guide = result.scalar_one_or_none()

    if not guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guide not found",
        )

    # Handle thumbnail update
    new_thumbnail_url = guide.thumbnail_url
    if thumbnail is not None and thumbnail.size and thumbnail.size > 0:
        try:
            file_content = await validate_image_upload(thumbnail)
            supabase = get_supabase()
            ext = thumbnail.filename.split(".")[-1] if thumbnail.filename and "." in thumbnail.filename else "png"
            filename = f"{uuid.uuid4()}.{ext}"

            supabase.storage.from_(BUCKET_NAME).upload(
                file=file_content,
                path=filename,
                file_options={"content-type": thumbnail.content_type or "image/png"},
            )
            new_thumbnail_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to upload new guide thumbnail")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload thumbnail. Please try again.",
            )

    # Regenerate slug if title changed
    new_slug = guide.slug
    if title != guide.title:
        new_slug = await _generate_unique_slug(db, title, exclude_id=guide.id)

    try:
        guide.title = title
        guide.slug = new_slug
        guide.guide_type = guide_type
        guide.description = description or None
        guide.thumbnail_url = new_thumbnail_url
        guide.content = content or None
        guide.youtube_url = youtube_url or None
        guide.tags = tags or None
        guide.author_name = author_name

        await db.commit()
        await db.refresh(guide)
        return guide
    except Exception:
        await db.rollback()
        logger.exception("Failed to update guide")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update guide. Please try again.",
        )


@router.delete("/{guide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guide(
    guide_id: int,
    current_user: Annotated[Any, Depends(require_admin)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a guide (Admin only)."""
    result = await db.execute(select(Guide).where(Guide.id == guide_id))
    guide = result.scalar_one_or_none()

    if not guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guide not found",
        )

    # Delete thumbnail from Supabase Storage
    if guide.thumbnail_url and BUCKET_NAME in guide.thumbnail_url:
        try:
            supabase = get_supabase()
            filename = guide.thumbnail_url.split("/")[-1]
            supabase.storage.from_(BUCKET_NAME).remove([filename])
        except Exception:
            logger.warning("Failed to delete guide thumbnail from Supabase", exc_info=True)

    await db.delete(guide)
    await db.commit()


# ─── Helpers ──────────────────────────────────────────────────────────


def _extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
