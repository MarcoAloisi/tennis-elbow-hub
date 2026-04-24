"""User Profile API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_supabase
from app.core.limiter import limiter
from app.models.user_profile import PlayerStatsOut, UserProfile, UserProfileOut, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["Profile"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


async def _get_or_create_profile(user: Any, db: AsyncSession) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        display_name = (getattr(user, "user_metadata", None) or {}).get("display_name", "")
        is_admin = (getattr(user, "app_metadata", None) or {}).get("role") == "admin"
        profile = UserProfile(
            id=user.id,
            display_name=display_name or "",
            approved=is_admin,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def _build_profile_out(profile: UserProfile) -> UserProfileOut:
    out = UserProfileOut.model_validate(profile)
    if profile.player_verified and profile.player_name:
        from app.services.stats_service import get_stats_service

        stats_service = get_stats_service()
        try:
            details = await stats_service.get_player_details_async(profile.player_name)
            if details:
                out.player_stats = PlayerStatsOut(
                    total_matches=details.get("total_matches", 0),
                    wins=details.get("wins", 0),
                    losses=details.get("losses", 0),
                    latest_elo=details.get("latest_elo"),
                    last_match_date=details.get("last_match_date"),
                )
        except Exception:
            pass
    return out


@router.get("/me", response_model=UserProfileOut)
@limiter.limit("60/minute")
async def get_my_profile(
    request: Request,
    user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get the authenticated user's profile (creates one if it doesn't exist)."""
    profile = await _get_or_create_profile(user, db)
    return await _build_profile_out(profile)


@router.put("/me", response_model=UserProfileOut)
@limiter.limit("60/minute")
async def update_my_profile(
    request: Request,
    updates: UserProfileUpdate,
    user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update the authenticated user's profile fields."""
    profile = await _get_or_create_profile(user, db)
    data = updates.model_dump(exclude_unset=True)

    if "player_name" in data and data["player_name"] != profile.player_name:
        data["player_verified"] = False

    if "tours" in data and data["tours"] is not None:
        valid = {"xkt", "wtsl"}
        if not all(t in valid for t in data["tours"]):
            raise HTTPException(status_code=422, detail="tours must contain only 'xkt' or 'wtsl'")

    for key, value in data.items():
        setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    return await _build_profile_out(profile)


@router.post("/me/avatar", response_model=UserProfileOut)
@limiter.limit("10/minute")
async def upload_avatar(
    request: Request,
    image: UploadFile = File(...),
    user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Upload or replace the authenticated user's avatar image."""
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="Image must be JPEG, PNG, or WebP")
    content = await image.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=422, detail="Image must be under 2MB")

    MIME_TO_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = MIME_TO_EXT.get(image.content_type, "jpg")
    path = f"{user.id}/avatar.{ext}"
    supabase = get_supabase()
    try:
        supabase.storage.from_("avatars").remove([path])
    except Exception:
        pass
    try:
        supabase.storage.from_("avatars").upload(
            file=content,
            path=path,
            file_options={"content-type": image.content_type or "image/png"},
        )
        public_url = supabase.storage.from_("avatars").get_public_url(path)
    except Exception:
        raise HTTPException(status_code=422, detail="Failed to upload avatar. Please try again.")

    profile = await _get_or_create_profile(user, db)
    profile.avatar_url = public_url
    await db.commit()
    await db.refresh(profile)
    return await _build_profile_out(profile)


@router.get("/{user_id}", response_model=UserProfileOut)
@limiter.limit("60/minute")
async def get_public_profile(
    request: Request,
    user_id: str,
    _user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get any user's public profile by their Supabase user ID."""
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return await _build_profile_out(profile)
