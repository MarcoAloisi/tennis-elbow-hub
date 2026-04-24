# User Profiles, Auth Emails & Sign-Up Flow

**Date:** 2026-04-24  
**Status:** Approved

---

## Overview

Three connected features:
1. **Custom branded emails** via Resend SMTP (welcome + password reset)
2. **User sign-up flow** with a `/reset-password` frontend route
3. **User profile dashboard** with stats linked to the player database

---

## 1. Custom Emails via Resend

### Setup
- Create a free Resend account, verify `tenniselbowhub.live` domain (add DNS TXT record in Cloudflare)
- Resend provides SMTP credentials: host `smtp.resend.com`, port 587
- Configure Supabase: **Project Settings → Auth → SMTP** with Resend credentials
- Sender: `noreply@tenniselbowhub.live`

### Templates (configured in Supabase dashboard)
Two email templates, both branded with TE4 Hub name/colors:

**Welcome email** — triggered on signup:
- Subject: "Welcome to Tennis Elbow Hub!"
- Body: greeting, confirm email button, link to site

**Password reset email** — triggered on reset request:
- Subject: "Reset your Tennis Elbow Hub password"
- Body: reset button linking to `https://tenniselbowhub.live/reset-password`
- Supabase appends token automatically via `{{ .ConfirmationURL }}`

---

## 2. Frontend Auth Flow Changes

### New routes
- `/reset-password` — handles Supabase token from email link, shows new password form, calls `supabase.auth.updateUser({ password })`
- `/signup` — email + password + display name form, calls existing `authStore.register()`

### Login page update
- Add "Sign up" link pointing to `/signup`
- Add "Forgot password?" link that triggers `supabase.auth.resetPasswordForEmail(email, { redirectTo: 'https://tenniselbowhub.live/reset-password' })`

### Auth store additions
- `resetPassword(email)` — calls Supabase reset password for email
- `updatePassword(newPassword)` — calls `supabase.auth.updateUser`

---

## 3. Database — `user_profiles` Table

New table via Alembic migration. One row per user, created automatically on first login or signup.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK, FK → Supabase `auth.users.id` |
| `display_name` | text | |
| `avatar_url` | text | Supabase Storage path |
| `bio` | text | nullable |
| `birthday` | date | nullable |
| `tours` | text[] | values: `xkt`, `wtsl` |
| `in_game_name` | text | nullable |
| `player_id` | integer | nullable, FK → players table |
| `player_verified` | boolean | default false |
| `favorite_tennis_player` | text | nullable |
| `favorite_tournament` | text | nullable |
| `created_at` | timestamp | auto, = member since date |

### Player link flow
1. User selects in-game name from dropdown (fetched from existing players endpoint)
2. `player_id` saved, `player_verified = false` → shows "pending approval" badge
3. Admin sees pending requests, approves or rejects
4. On approval: `player_verified = true` → profile shows player stats

---

## 4. Backend — New Endpoints

All profile endpoints require `get_current_user` dependency. Rate limited 60/minute.

### Profile endpoints (`/api/profile`)
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/profile/me` | Get own full profile |
| `PUT` | `/api/profile/me` | Update own profile fields |
| `POST` | `/api/profile/me/avatar` | Upload avatar → Supabase Storage |
| `GET` | `/api/profile/{user_id}` | Public profile (requires auth) |

### Admin endpoints (added to existing `/api/admin`)
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/admin/profile-verifications` | List pending player link requests |
| `POST` | `/api/admin/profile-verifications/{user_id}/approve` | Approve player link |
| `POST` | `/api/admin/profile-verifications/{user_id}/reject` | Reject, clears `player_id` |

### Profile auto-creation
On `GET /api/profile/me`, if no profile row exists yet, create one with defaults (display_name from Supabase user metadata).

### Player stats on profile
When `player_verified = true`, `GET /api/profile/{user_id}` includes a `player_stats` object pulled from existing player data (matches played, win rate, etc.).

---

## 5. Frontend — Profile Pages

### `/profile` (own profile, logged-in only)
- Edit mode toggle
- Avatar upload (crop + preview)
- Fields: display name, bio, birthday, tours (checkboxes: XKT / WTSL), in-game name (dropdown), favorite tennis player, favorite tournament
- Player link status badge: unlinked / pending / verified
- Stats section (visible when verified): matches played, win rate, from existing player DB
- Member since date (read-only, from `created_at`)

### `/profile/:userId` (public profile, logged-in only)
- Read-only view of another user's profile
- Same stats section if verified
- No edit controls

---

## 6. Supabase Storage

New bucket: `avatars` (public read, authenticated write)  
Path pattern: `avatars/{user_id}/avatar.{ext}`  
Max size: 2MB  
Accepted types: `image/jpeg`, `image/png`, `image/webp`

---

## 7. Out of Scope (future)

- Match log saving per user
- Public profiles for non-logged-in visitors
- Admin role assignment UI (still done via Supabase dashboard)
- Email notifications for verification approval/rejection (can be added later)
