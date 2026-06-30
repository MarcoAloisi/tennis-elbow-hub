# App Improvements Design — 2026-06-30

Four independent improvements to Tennis Elbow Hub.

---

## 1. Live Scores Flicker Fix

**Problem**: `isLoading` initializes as `false` in `frontend/src/stores/scores.ts`. One render cycle fires before `onMounted → fetchScores()` flips it to `true`, causing `isLoading=false + servers=[]` → the empty state ("No matches found") flashes for ~100ms on every page load.

**Fix**: Initialize `isLoading = ref<boolean>(true)` (line 19 of `stores/scores.ts`). The loading spinner now shows immediately; disappears when the first fetch resolves.

**Files changed**: `frontend/src/stores/scores.ts` (1 line).

---

## 2. Outfit Star Ratings

### Goal
Logged-in, approved users can rate outfits 1–5 stars. Anyone (including unauthenticated visitors) can see the average rating and count. One rating per user per outfit; users can update their rating.

### Backend

**New model** — `OutfitRating` in `backend/app/models/outfit.py`:
- `id` (PK), `outfit_id` (FK → outfits.id CASCADE DELETE), `user_id` (String), `rating` (Integer 1–5)
- UniqueConstraint on `(outfit_id, user_id)`

**Schema updates** — `OutfitResponse` gains two new fields:
- `avg_rating: float | None` — null when no ratings exist
- `rating_count: int` — default 0

**Endpoint updates**:
- `GET /api/outfits` — LEFT JOIN subquery computes `avg_rating` and `rating_count` per outfit; included in each item.
- `POST /api/outfits/{outfit_id}/rate` — requires `get_current_user`; body `{"rating": int}` (validated 1–5); upserts via INSERT … ON CONFLICT DO UPDATE. Returns updated `OutfitResponse` (with new avg).
- `GET /api/outfits/my-ratings` — requires `get_current_user`; returns `dict[int, int]` mapping `outfit_id → user_rating` for all outfits the current user has rated.

**Migration**: Alembic `revision --autogenerate` after adding `OutfitRating` model.

### Frontend

**New component** — `frontend/src/components/outfits/StarRating.vue`:
- Props: `avgRating: number | null`, `ratingCount: number`, `userRating: number | null`, `interactive: boolean`
- Renders 5 star icons. When `interactive=true`, hovering highlights stars and clicking calls `emit('rate', starIndex)`.
- Shows average as text ("4.2 ★ · 17 ratings") below the stars.

**`OutfitCard.vue` changes**:
- Add `StarRating` below the outfit title / above the meta row.
- Pass `outfit.avg_rating`, `outfit.rating_count`, `userRating` (from store), and `interactive = authStore.user != null`.
- On `@rate` event, call `outfitsStore.rateOutfit(outfit.id, rating)`.

**Outfits store additions** (`stores/outfits.ts`):
- `userRatings: ref<Record<number, number>>({})` — maps outfit_id → user's rating.
- `fetchUserRatings(token)` — calls `GET /api/outfits/my-ratings`, populates `userRatings`.
- `rateOutfit(outfitId, rating, token)` — calls `POST /api/outfits/{id}/rate`, updates `userRatings[outfitId]` and mutates the outfit's `avg_rating` / `rating_count` in `outfits` array optimistically (replace with server response).

**`OutfitGalleryView.vue` changes**:
- After outfits load, if `authStore.user` is set, call `outfitsStore.fetchUserRatings(token)`.
- Watch `authStore.user` — on login, fetch ratings; on logout, clear `userRatings`.

**Files changed**:
- `backend/app/models/outfit.py`
- `backend/app/api/endpoints/outfits.py`
- `backend/alembic/env.py` (import OutfitRating)
- `frontend/src/components/outfits/StarRating.vue` (new)
- `frontend/src/components/outfits/OutfitCard.vue`
- `frontend/src/stores/outfits.ts`
- `frontend/src/views/OutfitGalleryView.vue`

---

## 3. Community Signup Fix

**Not a code change.** Sign-ups are disabled in the Supabase project settings.

**Action**: Supabase Dashboard → **Authentication → Settings → "Allow new users to sign up" → ON**.

The existing `/signup` route, `SignupView.vue`, and approval gate all work correctly once this toggle is enabled. New users will see `/pending-approval` until an admin approves them via the Admin Panel.

---

## 4. XKT Build Analyzer — W.I.P. Section

Add a new section in `OnlineToursView.vue` inside the `v-if="currentTourKey === 'xkt'"` block, after the Tournament Predictions card (line ~192).

**UI**: A `tour-stats-section` div containing a card styled like the Predictions highlight card, but with:
- Title: "Build Analyzer"
- Icon: wrench or hammer (Lucide `Wrench`)
- A "Work in Progress" badge
- Short copy: "Analyze XKT player builds — coming soon."
- No link / no interaction

**Files changed**: `frontend/src/views/OnlineToursView.vue` (add section + import icon + CSS for WIP badge).
