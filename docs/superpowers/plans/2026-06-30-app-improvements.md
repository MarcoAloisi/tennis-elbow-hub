# App Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix live scores empty-state flash, add 1-5 star ratings to the Outfit Gallery, and add a WIP Build Analyzer section to the XKT tour tab.

**Architecture:** Task 1 is a one-line Pinia store fix. Task 2 is a full-stack feature: new `outfit_ratings` DB table, two new FastAPI endpoints, and the existing `GET /outfits` query updated to include avg/count via LEFT JOIN. Task 3 is the Vue side: a new `StarRating.vue` component wired into the existing store/card/view. Task 4 is a pure template addition with no new logic.

**Tech Stack:** FastAPI + SQLAlchemy (async) + Alembic · Vue 3 Composition API (`<script setup>`) + TypeScript + Pinia · Supabase Auth JWT

## Global Constraints

- Auth: use `get_current_user` dep from `app.api.deps` for protected endpoints (not `require_admin`)
- Rate limiting: `@limiter.limit("60/minute")` + `request: Request` param on all new auth-required routes
- All frontend API calls use `apiUrl()` from `@/config/api`
- Never use `Base.metadata.create_all()` — Alembic only for schema changes
- Import every new SQLAlchemy model in `backend/alembic/env.py` so Alembic detects it
- Scraper files untouched — `TennisTracker/1.0` UA must never change

## Supabase Config (No Code Needed)

> Go to **Supabase Dashboard → Authentication → Settings → "Allow new users to sign up" → toggle ON**.
> This fixes signups. No code change required. Approval gate stays as-is.

---

## File Map

| File | Action |
|------|--------|
| `frontend/src/stores/scores.ts` | Modify line 19: `isLoading = ref(true)` |
| `backend/app/models/outfit.py` | Add `OutfitRating` model, `RatingIn` schema, extend `OutfitResponse` |
| `backend/alembic/env.py` | Add `OutfitRating` to model imports |
| `backend/app/api/endpoints/outfits.py` | Add `GET /my-ratings`, `POST /{id}/rate`, update `GET /outfits` query |
| `backend/tests/test_outfit_ratings.py` | Create: schema/model unit tests |
| `frontend/src/components/outfits/StarRating.vue` | Create: interactive/readonly star display |
| `frontend/src/stores/outfits.ts` | Add `userRatings` state, `fetchUserRatings`, `rateOutfit` actions |
| `frontend/src/components/outfits/OutfitCard.vue` | Add `userRating` prop, embed `StarRating` |
| `frontend/src/views/OutfitGalleryView.vue` | Call `fetchUserRatings` on mount/login, pass `userRating` to cards |
| `frontend/src/views/OnlineToursView.vue` | Add Build Analyzer WIP section (XKT only) |

---

### Task 1: Live Scores Loading Flash Fix

**Files:**
- Modify: `frontend/src/stores/scores.ts:19`

**Interfaces:**
- Produces: `isLoading` starts `true`; `LiveScoresView.vue` template already handles this correctly (shows spinner when `isLoading && !servers.length`)

- [ ] **Step 1: Change `isLoading` initial value in `frontend/src/stores/scores.ts`**

Find line 19:
```typescript
const isLoading = ref<boolean>(false)
```
Change to:
```typescript
const isLoading = ref<boolean>(true)
```

- [ ] **Step 2: Manual verify**

Run `npm run dev` in `frontend/`. Navigate to `/live`. The loading spinner must appear immediately — no flash of "No matches found" before data loads. After data arrives the spinner disappears.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/scores.ts
git commit -m "fix: init isLoading=true in scores store to prevent empty-state flash on mount"
```

---

### Task 2: Outfit Ratings — Backend

**Files:**
- Modify: `backend/app/models/outfit.py`
- Modify: `backend/alembic/env.py`
- Modify: `backend/app/api/endpoints/outfits.py`
- Create: `backend/tests/test_outfit_ratings.py`

**Interfaces:**
- Produces:
  - `OutfitRating` SQLAlchemy model (table `outfit_ratings`)
  - `RatingIn` Pydantic schema: `{ rating: int }` validated 1–5
  - `OutfitResponse` gains `avg_rating: float | None = None` and `rating_count: int = 0`
  - `GET /api/outfits` — each item now includes `avg_rating` and `rating_count`
  - `GET /api/outfits/my-ratings` → `dict[int, int]` — requires auth
  - `POST /api/outfits/{outfit_id}/rate` → `OutfitResponse` — requires auth

- [ ] **Step 1: Replace `backend/app/models/outfit.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Outfit(Base):
    """Database model for Outfit Codes."""

    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    outfit_code: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    uploader_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index('ix_outfits_title_trgm', 'title', postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'}),
    )


class OutfitRating(Base):
    """One rating (1-5) per user per outfit."""

    __tablename__ = "outfit_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outfit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("outfit_id", "user_id", name="uq_outfit_rating_user"),
    )


class OutfitBase(BaseModel):
    """Base schema for Outfit."""
    title: str
    outfit_code: str
    category: str
    uploader_name: str


class OutfitCreate(OutfitBase):
    pass


class OutfitResponse(OutfitBase):
    """Schema for returning an Outfit."""
    id: int
    image_url: str
    created_at: datetime
    avg_rating: float | None = None
    rating_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PaginatedOutfitResponse(BaseModel):
    """Paginated response for outfit listings."""
    items: list[OutfitResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RatingIn(BaseModel):
    """Request body for rating an outfit."""
    rating: int = Field(..., ge=1, le=5)
```

- [ ] **Step 2: Update model import in `backend/alembic/env.py`**

Find the existing outfit model import. It will look like:
```python
from app.models.outfit import Outfit
```
Replace it with:
```python
from app.models.outfit import Outfit, OutfitRating  # noqa: F401
```

- [ ] **Step 3: Generate and apply migration**

```bash
cd backend
.venv/Scripts/alembic.exe revision --autogenerate -m "add outfit_ratings table"
.venv/Scripts/alembic.exe upgrade head
```

Open the generated file in `backend/alembic/versions/` and verify it:
- Creates table `outfit_ratings` with columns `id`, `outfit_id`, `user_id`, `rating`, `created_at`
- Has `ForeignKeyConstraint` on `outfit_id` referencing `outfits.id` with `ondelete="CASCADE"`
- Has `UniqueConstraint("outfit_id", "user_id", name="uq_outfit_rating_user")`

- [ ] **Step 4: Write tests — create `backend/tests/test_outfit_ratings.py`**

```python
"""Tests for outfit ratings model and schema."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.outfit import OutfitResponse, RatingIn


def test_rating_in_valid_range():
    for v in range(1, 6):
        assert RatingIn(rating=v).rating == v


def test_rating_in_rejects_zero():
    with pytest.raises(ValidationError):
        RatingIn(rating=0)


def test_rating_in_rejects_six():
    with pytest.raises(ValidationError):
        RatingIn(rating=6)


def test_outfit_response_rating_defaults():
    r = OutfitResponse(
        id=1,
        title="Test",
        outfit_code="code",
        category="Male",
        uploader_name="user",
        image_url="https://example.com/img.png",
        created_at=datetime.utcnow(),
    )
    assert r.avg_rating is None
    assert r.rating_count == 0


def test_outfit_response_with_rating():
    r = OutfitResponse(
        id=1,
        title="Test",
        outfit_code="code",
        category="Male",
        uploader_name="user",
        image_url="https://example.com/img.png",
        created_at=datetime.utcnow(),
        avg_rating=4.5,
        rating_count=10,
    )
    assert r.avg_rating == 4.5
    assert r.rating_count == 10
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd backend
pytest tests/test_outfit_ratings.py -v
```
Expected: 5 tests pass.

- [ ] **Step 6: Replace `backend/app/api/endpoints/outfits.py`**

> **Route ordering matters.** `GET /my-ratings` must be declared before `POST /{outfit_id}/rate` and `PUT/DELETE /{outfit_id}` so FastAPI doesn't try to match the literal string "my-ratings" as an `outfit_id` integer (which would fail with a 422, not a 404).

```python
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
            file_options={"content-type": image.content_type or "image/png"}
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
```

- [ ] **Step 7: Run full backend test suite**

```bash
cd backend
pytest -v
```
Expected: all tests pass, including the 5 new ones.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/outfit.py backend/alembic/env.py backend/app/api/endpoints/outfits.py backend/tests/test_outfit_ratings.py
git commit -m "feat: add outfit_ratings table, GET /my-ratings and POST /{id}/rate endpoints"
```

---

### Task 3: Outfit Ratings — Frontend

**Files:**
- Create: `frontend/src/components/outfits/StarRating.vue`
- Modify: `frontend/src/stores/outfits.ts`
- Modify: `frontend/src/components/outfits/OutfitCard.vue`
- Modify: `frontend/src/views/OutfitGalleryView.vue`

**Interfaces:**
- Consumes from Task 2: `outfit.avg_rating: number | null`, `outfit.rating_count: number` (on every outfit object)
- Consumes from Task 2: `GET /api/outfits/my-ratings` → `Record<number, number>`
- Consumes from Task 2: `POST /api/outfits/{id}/rate` body `{ rating: number }` → updated outfit

- [ ] **Step 1: Create `frontend/src/components/outfits/StarRating.vue`**

```vue
<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  avgRating: number | null
  ratingCount: number
  userRating: number | null
  interactive: boolean
}>()

const emit = defineEmits<{ rate: [value: number] }>()

const hovered = ref<number | null>(null)

function activeStars() {
  return hovered.value ?? props.userRating ?? 0
}

function starClass(star: number) {
  return activeStars() >= star ? 'filled' : 'empty'
}
</script>

<template>
  <div class="star-rating">
    <div class="stars" :class="{ interactive }">
      <button
        v-for="star in 5"
        :key="star"
        class="star-btn"
        :class="starClass(star)"
        :disabled="!interactive"
        :aria-label="`Rate ${star} star${star > 1 ? 's' : ''}`"
        @mouseenter="interactive && (hovered = star)"
        @mouseleave="interactive && (hovered = null)"
        @click="interactive && emit('rate', star)"
      >★</button>
    </div>
    <span v-if="ratingCount > 0" class="rating-meta">
      {{ avgRating?.toFixed(1) }} · {{ ratingCount }} {{ ratingCount === 1 ? 'rating' : 'ratings' }}
    </span>
    <span v-else class="rating-meta no-ratings">No ratings yet</span>
  </div>
</template>

<style scoped>
.star-rating {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.stars {
  display: flex;
  gap: 2px;
}

.star-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 1.1rem;
  line-height: 1;
  color: var(--color-border);
  cursor: default;
  transition: color 0.1s;
}

.star-btn.filled {
  color: #f59e0b;
}

.stars.interactive .star-btn {
  cursor: pointer;
}

.stars.interactive .star-btn:hover,
.stars.interactive .star-btn.filled {
  color: #f59e0b;
}

.rating-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.no-ratings {
  color: var(--color-text-muted);
}
</style>
```

- [ ] **Step 2: Add `userRatings`, `fetchUserRatings`, `rateOutfit` to `frontend/src/stores/outfits.ts`**

After `const pagination = ref(...)` (line ~15), add:
```typescript
const userRatings = ref<Record<number, number>>({})
```

After the `deleteOutfit` function, add:
```typescript
async function fetchUserRatings(token: string) {
    try {
        const response = await fetch(apiUrl('/api/outfits/my-ratings'), {
            headers: { Authorization: `Bearer ${token}` }
        })
        if (!response.ok) return
        userRatings.value = await response.json()
    } catch (err) {
        console.error('Failed to fetch user ratings:', err)
    }
}

async function rateOutfit(outfitId: number, rating: number, token: string) {
    const response = await fetch(apiUrl(`/api/outfits/${outfitId}/rate`), {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ rating }),
    })
    if (!response.ok) throw new Error('Failed to rate outfit')
    const updated = await response.json()
    const index = outfits.value.findIndex((o: any) => o.id === outfitId)
    if (index !== -1) {
        outfits.value[index] = { ...outfits.value[index], ...updated }
    }
    userRatings.value[outfitId] = rating
}
```

Add `userRatings`, `fetchUserRatings`, and `rateOutfit` to the `return` object at the bottom of the store.

- [ ] **Step 3: Modify `frontend/src/components/outfits/OutfitCard.vue`**

In `<script setup>`, add the `StarRating` import after the existing imports:
```typescript
import StarRating from '@/components/outfits/StarRating.vue'
```

Extend `defineProps` to add `userRating`:
```typescript
const props = defineProps({
  outfit: {
    type: Object,
    required: true
  },
  userRating: {
    type: Number,
    default: null
  }
})
```

In the `<template>`, add `<StarRating>` between `<h3 class="outfit-title">` and `<div class="meta-info">`:
```html
<h3 class="outfit-title">{{ outfit.title }}</h3>

<StarRating
  :avg-rating="outfit.avg_rating ?? null"
  :rating-count="outfit.rating_count ?? 0"
  :user-rating="userRating"
  :interactive="!!authStore.user"
  @rate="(val) => outfitsStore.rateOutfit(outfit.id, val, authStore.session?.access_token ?? '')"
/>

<div class="meta-info">
```

- [ ] **Step 4: Modify `frontend/src/views/OutfitGalleryView.vue`**

Add `watch` to the Vue import (line 2, currently `computed, onMounted, onUnmounted, ref`):
```typescript
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
```

In `onMounted` (currently lines 70-74), add the `fetchUserRatings` call after the existing fetches:
```typescript
onMounted(() => {
  outfitsStore.fetchOutfits()
  outfitsStore.fetchUploaders()
  window.addEventListener('paste', handlePaste)
  // Fetch user's existing ratings if already logged in
  if (authStore.user && authStore.session?.access_token) {
    outfitsStore.fetchUserRatings(authStore.session.access_token)
  }
})
```

After the `onUnmounted` block, add a watcher for auth state changes:
```typescript
watch(() => authStore.user, (user) => {
  if (user && authStore.session?.access_token) {
    outfitsStore.fetchUserRatings(authStore.session.access_token)
  } else {
    outfitsStore.userRatings = {}
  }
})
```

In the template, find the `<OutfitCard>` at line 271 and add the `user-rating` prop:
```html
<OutfitCard
  :outfit="outfit"
  :user-rating="outfitsStore.userRatings[outfit.id] ?? null"
  @edit="handleEditOutfit"
/>
```

- [ ] **Step 5: Type-check**

```bash
cd frontend
npm run type-check
```
Expected: no errors.

- [ ] **Step 6: Manual end-to-end test**

Start backend (`uvicorn app.main:app --reload` from `backend/`) and frontend (`npm run dev` from `frontend/`).

1. Navigate to `/outfit-gallery` — stars appear on each card showing "No ratings yet"
2. Log in as an approved user — stars become interactive (pointer cursor, hover highlights amber)
3. Click 4 stars on any card — the star display updates immediately, meta shows "4.0 · 1 rating"
4. Hard-refresh the page — the 4 stars remain highlighted (rating persisted in DB, re-fetched via `/my-ratings`)
5. Click 2 stars on the same card — updates to "2.0 · 1 rating" (upsert, not duplicate)
6. Log out — stars revert to read-only (no pointer, no hover)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/outfits/StarRating.vue frontend/src/stores/outfits.ts frontend/src/components/outfits/OutfitCard.vue frontend/src/views/OutfitGalleryView.vue
git commit -m "feat: add interactive star ratings to outfit gallery"
```

---

### Task 4: XKT Build Analyzer — W.I.P. Section

**Files:**
- Modify: `frontend/src/views/OnlineToursView.vue`

**Interfaces:**
- No API calls, no new props

- [ ] **Step 1: Add `Wrench` to the lucide import in `OnlineToursView.vue`**

Find line ~6:
```typescript
import { ChartNoAxesCombined, Gamepad2, Film, MousePointerClick, Globe, Video, Trophy } from 'lucide-vue-next'
```
Add `Wrench`:
```typescript
import { ChartNoAxesCombined, Gamepad2, Film, MousePointerClick, Globe, Video, Trophy, Wrench } from 'lucide-vue-next'
```

- [ ] **Step 2: Add the WIP section in the template**

After the closing `</div>` of the Tournament Predictions `tour-stats-section` (around line 192), add:

```html
<!-- Build Analyzer WIP (XKT only) -->
<div v-if="currentTourKey === 'xkt'" class="tour-stats-section">
  <h3>Build Analyzer</h3>
  <div class="link-card wip-card">
    <span class="link-icon-wrapper mod-build">
      <Wrench :size="24" stroke-width="2.5" />
    </span>
    <div class="tour-logs-content">
      <span class="link-label">
        Build Analyzer
        <span class="wip-badge">Work in Progress</span>
      </span>
      <span class="link-sublabel">Analyze XKT player builds — coming soon.</span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add CSS at the bottom of `<style scoped>`**

```css
.mod-build { color: #8b5cf6; background: rgba(139, 92, 246, 0.1); }

.wip-card {
  cursor: default;
  opacity: 0.75;
}

.wip-card:hover {
  transform: none;
  border-color: var(--color-border);
  background: var(--color-bg-secondary);
}

.wip-badge {
  display: inline-block;
  margin-left: var(--space-2);
  padding: 2px 8px;
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #8b5cf6;
  background: rgba(139, 92, 246, 0.12);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: var(--radius-full);
  vertical-align: middle;
}
```

- [ ] **Step 4: Manual verify**

Navigate to `/online-tours/xkt` — Build Analyzer card appears with the purple WIP badge. Card is non-interactive (no hover lift). Navigate to `/online-tours/wtsl` — section is absent.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/OnlineToursView.vue
git commit -m "feat: add Build Analyzer WIP section to XKT tour tab"
```
