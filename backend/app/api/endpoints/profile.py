"""User Profile API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.limiter import limiter
from app.models.user_profile import PlayerStatsOut, UserProfile, UserProfileOut, UserProfileUpdate
from app.services import local_storage

router = APIRouter(prefix="/profile", tags=["Profile"])

AVATAR_EXTENSIONS = ("jpg", "png", "webp", "gif")
MAX_AVATAR_SIZE_MB = 2


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


@router.get("/players")
@limiter.limit("60/minute")
async def get_player_names(
    request: Request,
    _user: Any = Depends(get_current_user),
) -> list[str]:
    """Return all canonical player names for the profile linking dropdown."""
    from app.services.stats_service import get_stats_service

    stats_service = get_stats_service()
    players = await stats_service.get_all_players_async()
    return sorted(p["name"] for p in players)


@router.get("/search")
@limiter.limit("30/minute")
async def search_profiles(
    request: Request,
    q: str = Query(..., min_length=2, max_length=50),
    _user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Search approved user profiles by display name."""
    result = await db.execute(
        select(UserProfile)
        .where(
            UserProfile.approved == True,  # noqa: E712
            UserProfile.display_name.ilike(f"%{q}%"),
        )
        .limit(20)
    )
    profiles = result.scalars().all()
    return [
        {
            "user_id": p.id,
            "display_name": p.display_name,
            "avatar_url": p.avatar_url,
            "player_name": p.player_name if p.player_verified else None,
            "player_verified": p.player_verified,
        }
        for p in profiles
    ]


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
    try:
        content, ext = await local_storage.process_upload(image, max_size_mb=MAX_AVATAR_SIZE_MB)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid image file.")

    settings = get_settings()
    for stale_ext in AVATAR_EXTENSIONS:
        local_storage.delete_file(
            "avatars", f"{user.id}/avatar.{stale_ext}", media_root=settings.media_root
        )

    try:
        public_url = local_storage.save_file(
            "avatars", f"{user.id}/avatar.{ext}", content,
            media_root=settings.media_root,
            base_url=settings.media_base_url,
            min_free_disk_mb=settings.min_free_disk_mb,
        )
    except HTTPException:
        raise
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
