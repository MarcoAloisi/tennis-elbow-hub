# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Tennis Elbow Hub — community platform for Tennis Elbow 4 players. Live scores via WebSocket, match log analysis, guides, outfit gallery, tour history, player stats.

## Commands

### Backend (run from `backend/`)

```bash
# Install
pip install -r requirements.txt
pip install -r requirements-dev.txt   # dev/test deps

# Run dev server
uvicorn app.main:app --reload

# Tests
pytest                                 # all tests
pytest tests/test_parser.py           # single file
pytest tests/test_parser.py::test_fn  # single test
pytest --cov=app                      # with coverage

# Lint / format
ruff check .
ruff format .

# Type check
mypy app/

# Alembic migrations
.venv/Scripts/alembic.exe revision --autogenerate -m "description"
.venv/Scripts/alembic.exe upgrade head
.venv/Scripts/alembic.exe downgrade -1
.venv/Scripts/alembic.exe current
```

### Frontend (run from `frontend/`)

```bash
npm install
npm run dev          # dev server at localhost:5173
npm run build        # type-check + vite build
npm run type-check   # vue-tsc only
npm run lint         # eslint fix
npm run test         # vitest
```

### Local dev (both services)

```powershell
./start-dev.ps1
```

## Architecture

### Backend (`backend/app/`)

- **`main.py`** — app factory. Mounts middleware (CORS, security headers, rate limiting), registers `api_router`, handles lifespan (DB init, scraper polling start/stop, stats flush on shutdown).
- **`api/endpoints/`** — one file per feature: `live_scores.py`, `guides.py`, `outfits.py`, `match_analysis.py`, `tour_logs.py`, `admin.py`, `players.py`, `predictions.py`, `contact.py`, `presence.py`.
- **`api/router.py`** — mounts all endpoint routers.
- **`api/deps.py`** — shared FastAPI dependencies: `get_db` (async DB session), `get_current_user` (Supabase JWT), `require_admin` (checks `app_metadata.role == "admin"`).
- **`core/config.py`** — `Settings` via `pydantic-settings`, loaded from `.env`.
- **`core/database.py`** — async SQLAlchemy engine + session factory. Uses `statement_cache_size=0` for Supabase pgbouncer compatibility.
- **`models/`** — SQLAlchemy ORM models + Pydantic schemas (co-located per feature).
- **`services/scraper.py`** — polls live scores URL, broadcasts via WebSocket `ConnectionManager`.
- **`services/presence.py`** — tracks site-wide online guest/registered counts, broadcasts via presence WebSocket.
- **`services/stats_service.py`** — in-memory stats accumulation, periodic DB flush.
- **`services/analyzer.py` + `parser.py`** — parse uploaded match log HTML (multilingual: EN/ES/PL), extract stats.

### Frontend (`frontend/src/`)

- **`config/api.ts`** — `apiUrl()` helper. All fetch calls must use this.
- **`stores/`** — Pinia global state (auth, live scores).
- **`composables/`** — view-local encapsulated logic (`useWebSocket`, `useAdminPlayers`, etc.).
- **`views/`** — page components.
- **`components/`** — reusable UI.

### Data flow

```
Scraper (httpx) → ConnectionManager → WebSocket → frontend scores store
Match log upload → parser.py → analyzer.py → ai_service.py (OpenRouter) → response
DB writes → async SQLAlchemy → PostgreSQL (prod) / SQLite (local)
Auth → Supabase JWT → deps.py get_current_user / require_admin
```

## Key Patterns

### New API endpoint

1. Add file (or route) in `backend/app/api/endpoints/`
2. Use `APIRouter(prefix="/feature", tags=["Feature"])`
3. Add `@limiter.limit("60/minute")` + `request: Request` param to every public route
4. Mount in `backend/app/api/router.py`
5. Paginate any list endpoint: `page: int = Query(default=1, ge=1)`, `page_size: int = Query(default=50, ge=1, le=200)`
6. Logged-in (non-admin) routes use `Depends(get_current_user)`. Player details: `GET /api/players/{name}?elo=` with required `elo` (`Query(..., ge=1)`). Do not use `/api/admin/players/{name}` (removed).

### New DB model

1. Add SQLAlchemy model in `backend/app/models/`
2. Import it in `backend/alembic/env.py` (so Alembic detects it)
3. Run `alembic revision --autogenerate` then `alembic upgrade head`
4. **Never use `Base.metadata.create_all()`** for schema changes — Alembic only

### Frontend API calls

```typescript
import { apiUrl } from '@/config/api'
const res = await fetch(apiUrl('/api/feature'))

// Auth header
const { data } = await supabase.auth.getSession()
const headers = { Authorization: `Bearer ${data.session?.access_token}` }

// Clustered player details — any logged-in user; required `elo` (ge=1)
await fetch(
  apiUrl(`/api/players/${encodeURIComponent(name)}?elo=${elo}`),
  { headers },
)
```

## Gotchas

- **Player names**: raw `match_name` values are lowercased for alias lookup in `player_aliases` table; canonical names preserve original casing.
- **Score filtering**: matches with < 5 total games are dropped (`StatsService.MIN_GAMES_THRESHOLD`).
- **Bot players**: names starting with `[.` are filtered from DB views.
- **Admin players endpoint**: returns all players unpaged (~200KB JSON). Admin-only; client filters. List rows are **one per ELO cluster** (same name may appear twice). Nickname mapper autocomplete uses unique names.
- **Player details**: `GET /api/players/{name}?elo=` — any logged-in user, cluster-scoped details. Do not use `/api/admin/players/{name}` (removed).
- **pgbouncer**: `statement_cache_size=0` is mandatory in `database.py` — do not remove.
- **`/docs`**: only enabled when `DEBUG=true` or `APP_ENV=development`.
- **Match log parser**: handles English, Spanish, and Polish stat labels. `def`/`vs`/`Przegrana` as winner separators.
- **Scraper User-Agent**: must always be `TennisTracker/1.0` — never change this value in any scraper (`scraper.py`, `tournament_scraper.py`). Managames whitelists this UA.
- **Presence state**: in-memory only in `services/presence.py`, single-process — not safe to assume shared counts across multiple backend instances/workers.

## Environment Variables

See `DEV_NOTES.md` for full table. Critical ones:

| Var | Notes |
|-----|-------|
| `DATABASE_URL` | PostgreSQL in prod; falls back to SQLite locally |
| `SUPABASE_URL` / `SUPABASE_KEY` | Service role key — backend only, never frontend |
| `CORS_ORIGINS` | Must match frontend domain exactly (prod) |
| `VITE_API_URL` | Backend URL for frontend build |
| `VITE_SUPABASE_ANON_KEY` | Public anon key — frontend only |

## Deployment

Render blueprint via `render.yaml`. Backend: Web Service → `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Pre-deploy: `alembic upgrade head`. Frontend: Static Site → `npm install && npm run build`, publish `dist/`.
