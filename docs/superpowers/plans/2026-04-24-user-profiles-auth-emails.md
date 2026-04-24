# User Profiles, Auth Emails & Sign-Up Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add custom branded emails via Resend, a /signup and /reset-password flow, and full user profile pages with player stats linking.

**Architecture:** New `user_profiles` SQLAlchemy model stores per-user data; new `/api/profile` FastAPI router handles CRUD + avatar upload; frontend gets SignupView, ResetPasswordView, and ProfileView. Player linking stores canonical player name (string) since players are derived from FinishedMatch records, not a DB table.

**Tech Stack:** FastAPI, SQLAlchemy (async), Supabase Auth + Storage, Vue 3 + Pinia, Resend SMTP

---

## Pre-Implementation Manual Steps (do these first, no code needed)

### Step A: Set up Resend SMTP
- [ ] Create account at resend.com
- [ ] Add domain: go to Domains → Add Domain → enter `tenniselbowhub.live`
- [ ] Resend gives you DNS records — add them in Cloudflare dashboard
- [ ] Once verified, go to API Keys → Create API Key → copy it
- [ ] In Supabase dashboard → Project Settings → Auth → SMTP:
  - Enable custom SMTP: ON
  - Host: `smtp.resend.com`
  - Port: `587`
  - Username: `resend`
  - Password: your Resend API key
  - Sender name: `Tennis Elbow Hub`
  - Sender email: `noreply@tenniselbowhub.live`

### Step B: Configure Supabase auth redirect URLs
- [ ] Supabase dashboard → Authentication → URL Configuration
- [ ] Site URL: `https://tenniselbowhub.live`
- [ ] Redirect URLs: add `https://tenniselbowhub.live/**`

### Step C: Create Supabase Storage avatars bucket
- [ ] Supabase dashboard → Storage → New bucket
- [ ] Name: `avatars`, Public: ON
- [ ] Set policy: authenticated users can upload to their own folder

### Step D: Configure Supabase email templates
- [ ] Supabase → Authentication → Email Templates → Confirm signup:
```html
<h2>Welcome to Tennis Elbow Hub!</h2>
<p>Thanks for joining the community. Click below to confirm your email.</p>
<a href="{{ .ConfirmationURL }}">Confirm Email</a>
```
- [ ] Supabase → Authentication → Email Templates → Reset Password:
```html
<h2>Reset your Tennis Elbow Hub password</h2>
<p>Click the link below to set a new password. This link expires in 1 hour.</p>
<a href="{{ .ConfirmationURL }}">Reset Password</a>
```

---

## File Map

**Create:**
- `backend/app/models/user_profile.py` — SQLAlchemy model + Pydantic schemas
- `backend/app/api/endpoints/profile.py` — profile CRUD + avatar upload endpoints
- `backend/tests/test_profile_api.py` — profile endpoint tests
- `frontend/src/views/SignupView.vue` — signup form
- `frontend/src/views/ResetPasswordView.vue` — new password form after email link
- `frontend/src/views/ProfileView.vue` — own profile dashboard (edit + view)
- `frontend/src/views/PublicProfileView.vue` — read-only profile for other users
- `frontend/src/composables/useProfile.ts` — profile API calls

**Modify:**
- `backend/alembic/env.py` — import UserProfile model so Alembic detects it
- `backend/app/api/router.py` — include profile router
- `backend/app/api/endpoints/admin.py` — add 3 verification endpoints
- `frontend/src/stores/auth.ts` — add `resetPassword()` and `updatePassword()`
- `frontend/src/views/LoginView.vue` — add signup + forgot password links
- `frontend/src/router/index.ts` — add /signup, /reset-password, /profile, /profile/:userId routes

---

## Task 1: UserProfile model and migration

**Files:**
- Create: `backend/app/models/user_profile.py`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Create the model file**

```python
# backend/app/models/user_profile.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel
from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Supabase user UUID
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tours: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True, default=list)
    in_game_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    player_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # canonical player name
    player_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    favorite_tennis_player: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    favorite_tournament: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Pydantic schemas
class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    birthday: Optional[date] = None
    tours: Optional[list[str]] = None
    in_game_name: Optional[str] = None
    player_name: Optional[str] = None
    favorite_tennis_player: Optional[str] = None
    favorite_tournament: Optional[str] = None


class PlayerStatsOut(BaseModel):
    total_matches: int
    wins: int
    losses: int
    latest_elo: Optional[int]
    last_match_date: Optional[str]


class UserProfileOut(BaseModel):
    id: str
    display_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    birthday: Optional[date]
    tours: Optional[list[str]]
    in_game_name: Optional[str]
    player_name: Optional[str]
    player_verified: bool
    favorite_tennis_player: Optional[str]
    favorite_tournament: Optional[str]
    created_at: datetime
    player_stats: Optional[PlayerStatsOut] = None

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Import model in alembic env.py**

Open `backend/alembic/env.py`. Find the block where other models are imported (look for lines like `from app.models.finished_match import FinishedMatch`). Add:

```python
from app.models.user_profile import UserProfile  # noqa: F401
```

- [ ] **Step 3: Generate and run migration**

```bash
cd backend
.venv/Scripts/alembic.exe revision --autogenerate -m "add user_profiles table"
.venv/Scripts/alembic.exe upgrade head
```

Expected output: `Running upgrade ... -> <hash>, add user_profiles table`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/user_profile.py backend/alembic/
git commit -m "feat: add user_profiles model and migration"
```

---

## Task 2: Profile API endpoints

**Files:**
- Create: `backend/app/api/endpoints/profile.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Write failing tests first**

Create `backend/tests/test_profile_api.py`:

```python
# backend/tests/test_profile_api.py
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

FAKE_USER_ID = "test-user-uuid-1234"

def fake_user():
    user = MagicMock()
    user.id = FAKE_USER_ID
    user.user_metadata = {"display_name": "TestUser"}
    return user

def test_get_my_profile_unauthenticated():
    response = client.get("/api/profile/me")
    assert response.status_code == 422  # missing auth header

def test_update_profile_unauthenticated():
    response = client.put("/api/profile/me", json={"display_name": "New Name"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail correctly**

```bash
cd backend
pytest tests/test_profile_api.py -v
```

Expected: both tests PASS (422 because no auth header — endpoint not created yet gives 404, so update expected to 404 for now, that's fine)

- [ ] **Step 3: Create the profile endpoints file**

```python
# backend/app/api/endpoints/profile.py
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_current_user, get_db, get_supabase
from app.models.user_profile import UserProfile, UserProfileOut, UserProfileUpdate, PlayerStatsOut
from app.services.stats_service import get_stats_service
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/profile", tags=["Profile"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


async def _get_or_create_profile(user: Any, db: AsyncSession) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        display_name = (getattr(user, "user_metadata", None) or {}).get("display_name", "")
        profile = UserProfile(id=user.id, display_name=display_name or "")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def _build_profile_out(profile: UserProfile) -> UserProfileOut:
    out = UserProfileOut.model_validate(profile)
    if profile.player_verified and profile.player_name:
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
):
    profile = await _get_or_create_profile(user, db)
    return await _build_profile_out(profile)


@router.put("/me", response_model=UserProfileOut)
@limiter.limit("60/minute")
async def update_my_profile(
    request: Request,
    updates: UserProfileUpdate,
    user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_or_create_profile(user, db)
    data = updates.model_dump(exclude_unset=True)

    # If player_name changed, reset verification
    if "player_name" in data and data["player_name"] != profile.player_name:
        data["player_verified"] = False

    # Validate tours values
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
):
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="Image must be JPEG, PNG, or WebP")
    content = await image.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=422, detail="Image must be under 2MB")

    ext = (image.filename or "avatar.png").split(".")[-1]
    path = f"{user.id}/avatar.{ext}"
    supabase = get_supabase()
    try:
        supabase.storage.from_("avatars").remove([path])
    except Exception:
        pass
    supabase.storage.from_("avatars").upload(
        file=content,
        path=path,
        file_options={"content-type": image.content_type or "image/png"},
    )
    public_url = supabase.storage.from_("avatars").get_public_url(path)

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
    _user: Any = Depends(get_current_user),  # require auth
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return await _build_profile_out(profile)
```

- [ ] **Step 4: Mount router in router.py**

Open `backend/app/api/router.py`. Add after the other imports and includes:

```python
from app.api.endpoints import profile
# ...
api_router.include_router(profile.router)
```

- [ ] **Step 5: Run the tests**

```bash
cd backend
pytest tests/test_profile_api.py -v
```

Expected: both tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/endpoints/profile.py backend/app/api/router.py backend/tests/test_profile_api.py
git commit -m "feat: add profile API endpoints"
```

---

## Task 3: Admin player verification endpoints

**Files:**
- Modify: `backend/app/api/endpoints/admin.py`

- [ ] **Step 1: Add three endpoints to admin.py**

Open `backend/app/api/endpoints/admin.py`. Add these imports at the top (after existing imports):

```python
from app.models.user_profile import UserProfile
```

Then add these three routes at the end of the file (before any closing code):

```python
@router.get("/profile-verifications")
@limiter.limit("60/minute")
async def list_pending_verifications(
    request: Request,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(
            UserProfile.player_name.isnot(None),
            UserProfile.player_verified == False,  # noqa: E712
        )
    )
    profiles = result.scalars().all()
    return [
        {
            "user_id": p.id,
            "display_name": p.display_name,
            "in_game_name": p.in_game_name,
            "player_name": p.player_name,
            "created_at": p.created_at,
        }
        for p in profiles
    ]


@router.post("/profile-verifications/{user_id}/approve")
@limiter.limit("60/minute")
async def approve_player_link(
    request: Request,
    user_id: str,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.player_verified = True
    await db.commit()
    return {"approved": True, "player_name": profile.player_name}


@router.post("/profile-verifications/{user_id}/reject")
@limiter.limit("60/minute")
async def reject_player_link(
    request: Request,
    user_id: str,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.player_name = None
    profile.player_verified = False
    await db.commit()
    return {"rejected": True}
```

- [ ] **Step 2: Check admin.py already imports AsyncSession and select**

Verify these imports exist at the top of `admin.py`. If not, add them:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db
```

- [ ] **Step 3: Run existing tests to make sure nothing broke**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/endpoints/admin.py
git commit -m "feat: add admin profile verification endpoints"
```

---

## Task 4: Frontend auth store additions + login page updates

**Files:**
- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/views/LoginView.vue`

- [ ] **Step 1: Add resetPassword and updatePassword to auth store**

Open `frontend/src/stores/auth.ts`. Find the `actions` section. Add after the existing `logout` action:

```typescript
async resetPassword(email: string): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const { error: err } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    if (err) throw err
  } catch (e: any) {
    error.value = e.message || 'Failed to send reset email'
    throw e
  } finally {
    loading.value = false
  }
},

async updatePassword(newPassword: string): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const { error: err } = await supabase.auth.updateUser({ password: newPassword })
    if (err) throw err
  } catch (e: any) {
    error.value = e.message || 'Failed to update password'
    throw e
  } finally {
    loading.value = false
  }
},
```

- [ ] **Step 2: Update LoginView.vue to add signup + forgot password links**

Open `frontend/src/views/LoginView.vue`. Find the submit button area and add below it:

```vue
<div class="auth-links">
  <router-link to="/signup" class="auth-link">Don't have an account? Sign up</router-link>
  <button
    type="button"
    class="auth-link-btn"
    @click="handleForgotPassword"
  >
    Forgot password?
  </button>
</div>
```

In the `<script setup>` section, add the forgot password handler:

```typescript
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const forgotEmail = ref('')

async function handleForgotPassword() {
  const email = prompt('Enter your email address:')
  if (!email) return
  try {
    await authStore.resetPassword(email)
    alert('Password reset email sent! Check your inbox.')
  } catch {
    alert('Failed to send reset email. Please try again.')
  }
}
```

Add minimal styles (or adapt to existing):
```css
.auth-links {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
}
.auth-link {
  color: var(--color-primary, #3b82f6);
  text-decoration: none;
  font-size: 14px;
}
.auth-link-btn {
  background: none;
  border: none;
  color: var(--color-primary, #3b82f6);
  font-size: 14px;
  cursor: pointer;
  padding: 0;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/auth.ts frontend/src/views/LoginView.vue
git commit -m "feat: add reset/update password to auth store, add login page links"
```

---

## Task 5: SignupView

**Files:**
- Create: `frontend/src/views/SignupView.vue`

- [ ] **Step 1: Create SignupView.vue**

```vue
<!-- frontend/src/views/SignupView.vue -->
<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Join Tennis Elbow Hub</h1>

      <form @submit.prevent="handleSignup">
        <div class="field">
          <label>Display Name</label>
          <input v-model="displayName" type="text" required placeholder="Your name" />
        </div>
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" required placeholder="you@email.com" />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="password" type="password" required placeholder="Min 6 characters" minlength="6" />
        </div>

        <p v-if="authStore.error" class="error">{{ authStore.error }}</p>
        <p v-if="success" class="success">Account created! Check your email to confirm.</p>

        <button type="submit" :disabled="authStore.loading">
          {{ authStore.loading ? 'Creating account...' : 'Sign Up' }}
        </button>
      </form>

      <div class="auth-links">
        <router-link to="/login" class="auth-link">Already have an account? Log in</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const displayName = ref('')
const email = ref('')
const password = ref('')
const success = ref(false)

async function handleSignup() {
  success.value = false
  try {
    await authStore.register(email.value, password.value, displayName.value)
    success.value = true
  } catch {
    // error shown via authStore.error
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
  padding: 2rem;
}
.auth-card {
  background: var(--color-surface, #1e1e2e);
  border-radius: 12px;
  padding: 2rem;
  width: 100%;
  max-width: 400px;
}
h1 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  text-align: center;
}
.field {
  margin-bottom: 1rem;
}
.field label {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
  opacity: 0.8;
}
.field input {
  width: 100%;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.05);
  color: inherit;
  font-size: 14px;
}
button[type="submit"] {
  width: 100%;
  padding: 12px;
  border-radius: 6px;
  background: var(--color-primary, #3b82f6);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 15px;
  margin-top: 8px;
}
button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #f87171; font-size: 14px; margin: 8px 0; }
.success { color: #4ade80; font-size: 14px; margin: 8px 0; }
.auth-links { margin-top: 16px; text-align: center; }
.auth-link { color: var(--color-primary, #3b82f6); font-size: 14px; text-decoration: none; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/SignupView.vue
git commit -m "feat: add SignupView"
```

---

## Task 6: ResetPasswordView

**Files:**
- Create: `frontend/src/views/ResetPasswordView.vue`

- [ ] **Step 1: Create ResetPasswordView.vue**

```vue
<!-- frontend/src/views/ResetPasswordView.vue -->
<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Set New Password</h1>

      <form @submit.prevent="handleReset">
        <div class="field">
          <label>New Password</label>
          <input v-model="password" type="password" required placeholder="Min 6 characters" minlength="6" />
        </div>
        <div class="field">
          <label>Confirm Password</label>
          <input v-model="confirm" type="password" required placeholder="Repeat password" />
        </div>

        <p v-if="mismatch" class="error">Passwords do not match</p>
        <p v-if="authStore.error" class="error">{{ authStore.error }}</p>
        <p v-if="success" class="success">Password updated! You can now log in.</p>

        <button type="submit" :disabled="authStore.loading">
          {{ authStore.loading ? 'Updating...' : 'Update Password' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const password = ref('')
const confirm = ref('')
const mismatch = ref(false)
const success = ref(false)

async function handleReset() {
  mismatch.value = false
  if (password.value !== confirm.value) {
    mismatch.value = true
    return
  }
  try {
    await authStore.updatePassword(password.value)
    success.value = true
    setTimeout(() => router.push('/login'), 2000)
  } catch {
    // error shown via authStore.error
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
  padding: 2rem;
}
.auth-card {
  background: var(--color-surface, #1e1e2e);
  border-radius: 12px;
  padding: 2rem;
  width: 100%;
  max-width: 400px;
}
h1 { font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center; }
.field { margin-bottom: 1rem; }
.field label { display: block; margin-bottom: 4px; font-size: 14px; opacity: 0.8; }
.field input {
  width: 100%;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.05);
  color: inherit;
  font-size: 14px;
}
button[type="submit"] {
  width: 100%;
  padding: 12px;
  border-radius: 6px;
  background: var(--color-primary, #3b82f6);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 15px;
  margin-top: 8px;
}
button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #f87171; font-size: 14px; margin: 8px 0; }
.success { color: #4ade80; font-size: 14px; margin: 8px 0; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ResetPasswordView.vue
git commit -m "feat: add ResetPasswordView"
```

---

## Task 7: Profile composable

**Files:**
- Create: `frontend/src/composables/useProfile.ts`

- [ ] **Step 1: Create useProfile.ts**

```typescript
// frontend/src/composables/useProfile.ts
import { ref } from 'vue'
import { apiUrl } from '@/config/api'
import { supabase } from '@/config/supabase'

export interface PlayerStats {
  total_matches: number
  wins: number
  losses: number
  latest_elo: number | null
  last_match_date: string | null
}

export interface Profile {
  id: string
  display_name: string
  avatar_url: string | null
  bio: string | null
  birthday: string | null
  tours: string[] | null
  in_game_name: string | null
  player_name: string | null
  player_verified: boolean
  favorite_tennis_player: string | null
  favorite_tournament: string | null
  created_at: string
  player_stats: PlayerStats | null
}

export interface ProfileUpdate {
  display_name?: string
  bio?: string
  birthday?: string | null
  tours?: string[]
  in_game_name?: string
  player_name?: string | null
  favorite_tennis_player?: string
  favorite_tournament?: string
}

async function authHeaders(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession()
  return { Authorization: `Bearer ${data.session?.access_token}` }
}

export function useProfile() {
  const profile = ref<Profile | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchMyProfile(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const res = await fetch(apiUrl('/api/profile/me'), { headers })
      if (!res.ok) throw new Error('Failed to load profile')
      profile.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPublicProfile(userId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const res = await fetch(apiUrl(`/api/profile/${userId}`), { headers })
      if (!res.ok) throw new Error('Profile not found')
      profile.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(updates: ProfileUpdate): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const res = await fetch(apiUrl('/api/profile/me'), {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (!res.ok) throw new Error('Failed to update profile')
      profile.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function uploadAvatar(file: File): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const form = new FormData()
      form.append('image', file)
      const res = await fetch(apiUrl('/api/profile/me/avatar'), {
        method: 'POST',
        headers,
        body: form,
      })
      if (!res.ok) throw new Error('Failed to upload avatar')
      profile.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPlayers(): Promise<string[]> {
    try {
      const headers = await authHeaders()
      const res = await fetch(apiUrl('/api/admin/players'), { headers })
      if (!res.ok) return []
      const data: { name: string }[] = await res.json()
      return data.map((p) => p.name).sort()
    } catch {
      return []
    }
  }

  return { profile, loading, error, fetchMyProfile, fetchPublicProfile, updateProfile, uploadAvatar, fetchPlayers }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useProfile.ts
git commit -m "feat: add useProfile composable"
```

---

## Task 8: ProfileView (own profile dashboard)

**Files:**
- Create: `frontend/src/views/ProfileView.vue`

- [ ] **Step 1: Create ProfileView.vue**

```vue
<!-- frontend/src/views/ProfileView.vue -->
<template>
  <div class="profile-page">
    <div v-if="loading" class="loading">Loading profile...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="profile" class="profile-container">

      <!-- Avatar -->
      <div class="avatar-section">
        <img :src="profile.avatar_url || defaultAvatar" class="avatar" alt="Avatar" />
        <div v-if="editMode">
          <input type="file" accept="image/jpeg,image/png,image/webp" @change="handleAvatarChange" />
          <p class="hint">Max 2MB. JPEG, PNG, WebP.</p>
        </div>
      </div>

      <!-- Header info -->
      <div class="profile-header">
        <h1>{{ profile.display_name || 'No name set' }}</h1>
        <p class="member-since">Member since {{ memberSince }}</p>
        <button class="edit-btn" @click="toggleEdit">{{ editMode ? 'Cancel' : 'Edit Profile' }}</button>
      </div>

      <!-- View mode -->
      <div v-if="!editMode" class="profile-info">
        <p v-if="profile.bio" class="bio">{{ profile.bio }}</p>
        <div class="fields">
          <div v-if="profile.in_game_name" class="field-row">
            <span class="label">In-Game Name</span>
            <span>{{ profile.in_game_name }}
              <span v-if="profile.player_verified" class="badge verified">Verified</span>
              <span v-else-if="profile.player_name" class="badge pending">Pending</span>
            </span>
          </div>
          <div v-if="profile.tours?.length" class="field-row">
            <span class="label">Tours</span>
            <span>{{ profile.tours.map(t => t.toUpperCase()).join(', ') }}</span>
          </div>
          <div v-if="profile.favorite_tennis_player" class="field-row">
            <span class="label">Favorite Player</span>
            <span>{{ profile.favorite_tennis_player }}</span>
          </div>
          <div v-if="profile.favorite_tournament" class="field-row">
            <span class="label">Favorite Tournament</span>
            <span>{{ profile.favorite_tournament }}</span>
          </div>
          <div v-if="profile.birthday" class="field-row">
            <span class="label">Birthday</span>
            <span>{{ profile.birthday }}</span>
          </div>
        </div>

        <!-- Player stats -->
        <div v-if="profile.player_verified && profile.player_stats" class="stats-section">
          <h2>Player Stats</h2>
          <div class="stats-grid">
            <div class="stat"><span class="stat-val">{{ profile.player_stats.total_matches }}</span><span class="stat-label">Matches</span></div>
            <div class="stat"><span class="stat-val">{{ profile.player_stats.wins }}</span><span class="stat-label">Wins</span></div>
            <div class="stat"><span class="stat-val">{{ profile.player_stats.losses }}</span><span class="stat-label">Losses</span></div>
            <div class="stat"><span class="stat-val">{{ profile.player_stats.latest_elo ?? '—' }}</span><span class="stat-label">ELO</span></div>
          </div>
        </div>
      </div>

      <!-- Edit mode -->
      <form v-else class="edit-form" @submit.prevent="saveProfile">
        <div class="field">
          <label>Display Name</label>
          <input v-model="form.display_name" type="text" />
        </div>
        <div class="field">
          <label>Bio</label>
          <textarea v-model="form.bio" rows="3"></textarea>
        </div>
        <div class="field">
          <label>Birthday</label>
          <input v-model="form.birthday" type="date" />
        </div>
        <div class="field">
          <label>Tours</label>
          <label class="checkbox"><input type="checkbox" value="xkt" v-model="form.tours" /> XKT</label>
          <label class="checkbox"><input type="checkbox" value="wtsl" v-model="form.tours" /> WTSL</label>
        </div>
        <div class="field">
          <label>In-Game Name</label>
          <input v-model="form.in_game_name" type="text" placeholder="Your in-game name" />
        </div>
        <div class="field">
          <label>Link to Player (select from database)</label>
          <select v-model="form.player_name">
            <option value="">— not linked —</option>
            <option v-for="p in players" :key="p" :value="p">{{ p }}</option>
          </select>
          <p class="hint">Requires admin approval to show stats.</p>
        </div>
        <div class="field">
          <label>Favorite Tennis Player</label>
          <input v-model="form.favorite_tennis_player" type="text" />
        </div>
        <div class="field">
          <label>Favorite Tournament</label>
          <input v-model="form.favorite_tournament" type="text" />
        </div>

        <p v-if="saveError" class="error">{{ saveError }}</p>
        <button type="submit" :disabled="saving">{{ saving ? 'Saving...' : 'Save Changes' }}</button>
      </form>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProfile } from '@/composables/useProfile'

const { profile, loading, error, fetchMyProfile, updateProfile, uploadAvatar, fetchPlayers } = useProfile()

const editMode = ref(false)
const saving = ref(false)
const saveError = ref<string | null>(null)
const players = ref<string[]>([])
const defaultAvatar = 'https://ui-avatars.com/api/?background=3b82f6&color=fff&name=TE4'

const form = ref({
  display_name: '',
  bio: '',
  birthday: '',
  tours: [] as string[],
  in_game_name: '',
  player_name: '',
  favorite_tennis_player: '',
  favorite_tournament: '',
})

const memberSince = computed(() => {
  if (!profile.value) return ''
  return new Date(profile.value.created_at).toLocaleDateString('en-GB', { year: 'numeric', month: 'long' })
})

function toggleEdit() {
  if (!editMode.value && profile.value) {
    form.value = {
      display_name: profile.value.display_name || '',
      bio: profile.value.bio || '',
      birthday: profile.value.birthday || '',
      tours: profile.value.tours || [],
      in_game_name: profile.value.in_game_name || '',
      player_name: profile.value.player_name || '',
      favorite_tennis_player: profile.value.favorite_tennis_player || '',
      favorite_tournament: profile.value.favorite_tournament || '',
    }
  }
  editMode.value = !editMode.value
}

async function saveProfile() {
  saving.value = true
  saveError.value = null
  try {
    await updateProfile({
      ...form.value,
      birthday: form.value.birthday || null,
      player_name: form.value.player_name || null,
    })
    editMode.value = false
  } catch (e: any) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

async function handleAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  await uploadAvatar(file)
}

onMounted(async () => {
  await fetchMyProfile()
  players.value = await fetchPlayers()
})
</script>

<style scoped>
.profile-page { max-width: 700px; margin: 2rem auto; padding: 0 1rem; }
.loading, .error { text-align: center; padding: 2rem; }
.error { color: #f87171; }
.avatar-section { text-align: center; margin-bottom: 1rem; }
.avatar { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 3px solid var(--color-primary, #3b82f6); }
.profile-header { text-align: center; margin-bottom: 1.5rem; }
.profile-header h1 { font-size: 1.8rem; margin-bottom: 4px; }
.member-since { opacity: 0.6; font-size: 14px; margin-bottom: 12px; }
.edit-btn { padding: 8px 20px; border-radius: 6px; border: 1px solid var(--color-primary, #3b82f6); background: transparent; color: var(--color-primary, #3b82f6); cursor: pointer; }
.bio { opacity: 0.8; margin-bottom: 1rem; line-height: 1.6; }
.fields { display: flex; flex-direction: column; gap: 10px; margin-bottom: 1.5rem; }
.field-row { display: flex; gap: 12px; }
.label { font-weight: 600; min-width: 160px; opacity: 0.7; font-size: 14px; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 99px; margin-left: 8px; }
.badge.verified { background: #4ade80; color: #000; }
.badge.pending { background: #facc15; color: #000; }
.stats-section { margin-top: 2rem; }
.stats-section h2 { font-size: 1.2rem; margin-bottom: 1rem; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 1rem; text-align: center; }
.stat-val { display: block; font-size: 1.8rem; font-weight: 700; }
.stat-label { font-size: 12px; opacity: 0.6; }
.edit-form .field { margin-bottom: 1rem; }
.edit-form label { display: block; font-size: 14px; opacity: 0.8; margin-bottom: 4px; }
.edit-form input, .edit-form textarea, .edit-form select {
  width: 100%;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.05);
  color: inherit;
  font-size: 14px;
}
.checkbox { display: inline-flex; align-items: center; gap: 6px; margin-right: 16px; cursor: pointer; }
.hint { font-size: 12px; opacity: 0.5; margin-top: 4px; }
button[type="submit"] {
  padding: 12px 32px;
  border-radius: 6px;
  background: var(--color-primary, #3b82f6);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 15px;
}
button:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ProfileView.vue
git commit -m "feat: add ProfileView dashboard"
```

---

## Task 9: PublicProfileView

**Files:**
- Create: `frontend/src/views/PublicProfileView.vue`

- [ ] **Step 1: Create PublicProfileView.vue**

```vue
<!-- frontend/src/views/PublicProfileView.vue -->
<template>
  <div class="profile-page">
    <div v-if="loading" class="loading">Loading profile...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="profile" class="profile-container">

      <div class="avatar-section">
        <img :src="profile.avatar_url || defaultAvatar" class="avatar" alt="Avatar" />
      </div>

      <div class="profile-header">
        <h1>{{ profile.display_name || 'Player' }}</h1>
        <p class="member-since">Member since {{ memberSince }}</p>
      </div>

      <div class="profile-info">
        <p v-if="profile.bio" class="bio">{{ profile.bio }}</p>
        <div class="fields">
          <div v-if="profile.in_game_name" class="field-row">
            <span class="label">In-Game Name</span>
            <span>{{ profile.in_game_name }}
              <span v-if="profile.player_verified" class="badge verified">Verified</span>
            </span>
          </div>
          <div v-if="profile.tours?.length" class="field-row">
            <span class="label">Tours</span>
            <span>{{ profile.tours.map(t => t.toUpperCase()).join(', ') }}</span>
          </div>
          <div v-if="profile.favorite_tennis_player" class="field-row">
            <span class="label">Favorite Player</span>
            <span>{{ profile.favorite_tennis_player }}</span>
          </div>
          <div v-if="profile.favorite_tournament" class="field-row">
            <span class="label">Favorite Tournament</span>
            <span>{{ profile.favorite_tournament }}</span>
          </div>
        </div>

        <div v-if="profile.player_verified && profile.player_stats" class="stats-section">
          <h2>Player Stats</h2>
          <div class="stats-grid">
            <div class="stat"><span class="stat-val">{{ profile.player_stats.total_matches }}</span><span class="stat-label">Matches</span></div>
            <div class="stat"><span class="stat-val">{{ profile.player_stats.wins }}</span><span class="stat-label">Wins</span></div>
            <div class="stat"><span class="stat-val">{{ profile.player_stats.losses }}</span><span class="stat-label">Losses</span></div>
            <div class="stat"><span class="stat-val">{{ profile.player_stats.latest_elo ?? '—' }}</span><span class="stat-label">ELO</span></div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProfile } from '@/composables/useProfile'

const route = useRoute()
const { profile, loading, error, fetchPublicProfile } = useProfile()
const defaultAvatar = 'https://ui-avatars.com/api/?background=3b82f6&color=fff&name=TE4'

const memberSince = computed(() => {
  if (!profile.value) return ''
  return new Date(profile.value.created_at).toLocaleDateString('en-GB', { year: 'numeric', month: 'long' })
})

onMounted(() => fetchPublicProfile(route.params.userId as string))
</script>

<style scoped>
.profile-page { max-width: 700px; margin: 2rem auto; padding: 0 1rem; }
.loading, .error { text-align: center; padding: 2rem; }
.error { color: #f87171; }
.avatar-section { text-align: center; margin-bottom: 1rem; }
.avatar { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 3px solid var(--color-primary, #3b82f6); }
.profile-header { text-align: center; margin-bottom: 1.5rem; }
.profile-header h1 { font-size: 1.8rem; margin-bottom: 4px; }
.member-since { opacity: 0.6; font-size: 14px; }
.bio { opacity: 0.8; margin-bottom: 1rem; line-height: 1.6; }
.fields { display: flex; flex-direction: column; gap: 10px; margin-bottom: 1.5rem; }
.field-row { display: flex; gap: 12px; }
.label { font-weight: 600; min-width: 160px; opacity: 0.7; font-size: 14px; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 99px; margin-left: 8px; }
.badge.verified { background: #4ade80; color: #000; }
.stats-section { margin-top: 2rem; }
.stats-section h2 { font-size: 1.2rem; margin-bottom: 1rem; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 1rem; text-align: center; }
.stat-val { display: block; font-size: 1.8rem; font-weight: 700; }
.stat-label { font-size: 12px; opacity: 0.6; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/PublicProfileView.vue
git commit -m "feat: add PublicProfileView"
```

---

## Task 10: Router updates

**Files:**
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Add new routes to router**

Open `frontend/src/router/index.ts`. Find the `routes` array. Add these four routes (the profile routes should require auth — use the same `requiresAuth` meta pattern already present in the file):

```typescript
{
  path: '/signup',
  name: 'Signup',
  component: () => import('@/views/SignupView.vue'),
},
{
  path: '/reset-password',
  name: 'ResetPassword',
  component: () => import('@/views/ResetPasswordView.vue'),
},
{
  path: '/profile',
  name: 'Profile',
  component: () => import('@/views/ProfileView.vue'),
  meta: { requiresAuth: true },
},
{
  path: '/profile/:userId',
  name: 'PublicProfile',
  component: () => import('@/views/PublicProfileView.vue'),
  meta: { requiresAuth: true },
},
```

- [ ] **Step 2: Verify type-check passes**

```bash
cd frontend
npm run type-check
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat: add signup, reset-password, and profile routes"
```

---

## Task 11: CSP update for Resend + push

**Files:**
- Modify: `frontend/public/_headers`

- [ ] **Step 1: No CSP changes needed**

Resend sends emails server-side (Supabase → Resend) — no frontend fetch to Resend. Skip this task.

- [ ] **Step 2: Push all commits**

```bash
git push origin ionos-migration
```

- [ ] **Step 3: On VPS, pull and restart**

```bash
cd /var/www/te4
git pull origin ionos-migration
cd backend
.venv/bin/alembic upgrade head
sudo systemctl restart te4-backend
```

---

## Testing Checklist

After deploying:
- [ ] `/signup` — create a new account, check welcome email arrives from `noreply@tenniselbowhub.live`
- [ ] `/login` → Forgot password → check reset email → `/reset-password` → set new password → login works
- [ ] `/profile` — loads, edit mode works, saves correctly
- [ ] Avatar upload — uploads, shows on profile
- [ ] Player dropdown — shows player list, selecting one shows "Pending" badge
- [ ] Admin panel → profile verifications → approve → player stats appear on profile
- [ ] `/profile/:userId` — logged-in user can view another user's profile
- [ ] `/profile/:userId` — logged-out user is redirected to login
