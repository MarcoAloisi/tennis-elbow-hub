# Instagram CTA Widget — Design Spec

**Date:** 2026-06-26

## Goal

Prompt visitors to follow the Tennis Elbow 4 Instagram page (`@te4__tv`) for video content.

## Behaviour

- Appears **5 seconds** after page load
- **Session-scoped:** uses `sessionStorage` key `ig_cta_dismissed`. Once dismissed, hidden for the rest of the session. Reappears on next visit.
- Never blocks content — corner card only

## Component

**File:** `frontend/src/components/common/InstagramCTA.vue`

Self-contained. Mirrors the `KofiWidget` / `CookieConsent` pattern.

### Layout

- Fixed position: **bottom-left** corner (KoFi sits bottom-right — no overlap)
- Slide-up `<Transition>` on appear (same animation pattern as `CookieConsent`)
- Uses existing CSS design tokens (`--color-surface`, `--color-border`, `--space-*`, `--radius-*`, `--shadow-*`)

### Content

```
┌─────────────────────────────┐  ← corner card, ~280px wide
│  [IG gradient icon]         [×]│
│  Follow us on Instagram!       │
│  @te4__tv — videos & content  │
│  [Follow →]                    │
└─────────────────────────────┘
```

- Instagram icon: SVG inline (no new dependency)
- "Follow →" button: opens `https://www.instagram.com/te4__tv/` in new tab
- `×` close button: sets `sessionStorage.ig_cta_dismissed = '1'`, hides component

### Logic (script setup)

```ts
const DISMISSED_KEY = 'ig_cta_dismissed'
const visible = ref(false)

onMounted(() => {
  if (!sessionStorage.getItem(DISMISSED_KEY)) {
    setTimeout(() => { visible.value = true }, 5000)
  }
})

function dismiss() {
  sessionStorage.setItem(DISMISSED_KEY, '1')
  visible.value = false
}
```

## Mount point

`frontend/src/App.vue` — one import + one tag alongside `<KofiWidget>` and `<CookieConsent>`.

## Out of scope

- Page-specific targeting (shows globally — fine for now)
- Permanent dismiss (sessionStorage only, as agreed)
- Embed/preview of actual IG feed (no API needed)
