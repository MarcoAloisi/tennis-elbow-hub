<div align="center">

```
████████╗███████╗██╗  ██╗    ██╗  ██╗██╗   ██╗██████╗
╚══██╔══╝██╔════╝██║  ██║    ██║  ██║██║   ██║██╔══██╗
   ██║   █████╗  ███████║    ███████║██║   ██║██████╔╝
   ██║   ██╔══╝  ╚════██║    ██╔══██║██║   ██║██╔══██╗
   ██║   ███████╗     ██║    ██║  ██║╚██████╔╝██████╔╝
   ╚═╝   ╚══════╝     ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝
```

**The community hub for Tennis Elbow 4 — live scores, match analysis, guides, and more.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vue.js&logoColor=white)](https://vuejs.org)
[![Supabase](https://img.shields.io/badge/Supabase-Auth%20%2B%20Storage-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Prod%20DB-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Deployed on Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=flat-square&logo=render&logoColor=white)](https://render.com)

</div>

---

## Overview

Tennis Elbow Hub is a full-stack web application built for the Tennis Elbow 4 community. It aggregates live match scores via WebSocket broadcasting, provides deep match statistics through HTML log parsing, and hosts a community-curated knowledge base of guides, outfits, and tour logs.

---

## Features

| Feature | Description |
|---|---|
| **Live Scores** | Real-time match scores streamed via WebSocket with auto-reconnect (exponential backoff) |
| **Match Analysis** | Upload `.html` match log files — get detailed player stats, game breakdowns, and head-to-head comparisons powered by AI |
| **Guides** | Curated written guides and video walkthroughs, filterable by tag, type, and keyword |
| **Outfit Gallery** | Community outfit codes with screenshots, categories, and copy-to-clipboard support |
| **Tour Logs** | Paginated log of tour match results with player filtering |
| **Online Tours** | Dedicated section for online tournament information |
| **Player Stats** | Per-player win/loss records, match history, and daily stats with timezone-aware resets |
| **Admin Panel** | Full CRUD for guides, outfits, and player alias management — gated behind Supabase JWT role |
| **Contact** | SMTP contact form routed to a configured inbox |
| **Dark / Light Theme** | Persistent theme toggle |

---

## Tech Stack

### Backend

| Layer | Technology |
|---|---|
| Runtime | Python 3.11+ |
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Database | PostgreSQL (prod) · SQLite (local dev) |
| Auth | Supabase JWT (`HS256`) |
| File Storage | Supabase Storage |
| Rate Limiting | slowapi |
| AI | OpenRouter API |
| Server | Uvicorn |

### Frontend

| Layer | Technology |
|---|---|
| Framework | Vue 3 (Composition API) |
| Build Tool | Vite |
| State | Pinia |
| Charts | Chart.js + vue-chartjs |
| Rich Text | TipTap editor |
| Auth Client | Supabase JS |

---

## Project Structure

```
TE4-PROJECT/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/        # One file per feature
│   │   │   │   ├── admin.py      # Player DB management
│   │   │   │   ├── contact.py    # SMTP contact form
│   │   │   │   ├── guides.py     # Guides CRUD + image uploads
│   │   │   │   ├── live_scores.py # WebSocket score broadcasting
│   │   │   │   ├── match_analysis.py # Log parsing + AI analysis
│   │   │   │   ├── outfits.py    # Outfit gallery CRUD
│   │   │   │   └── tour_logs.py  # Paginated tour log history
│   │   │   ├── deps.py           # Auth + DB session dependencies
│   │   │   └── router.py         # Mounts all routers under /api
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic settings (env-driven)
│   │   │   ├── database.py       # Async engine + session factory
│   │   │   ├── limiter.py        # slowapi rate limiter
│   │   │   ├── logging.py        # Structured logging setup
│   │   │   ├── security.py       # Image validation, security headers
│   │   │   └── utils.py          # Shared helpers (escape_like, etc.)
│   │   ├── models/               # SQLAlchemy models + Pydantic schemas
│   │   ├── services/             # Business logic (scraper, stats, analyzer)
│   │   └── main.py               # App factory, middleware, health check
│   ├── alembic/                  # Database migrations
│   │   └── versions/
│   ├── requirements.txt
│   └── tests/
│
└── frontend/
    └── src/
        ├── components/           # Reusable UI components
        ├── composables/          # Encapsulated view-local logic
        ├── config/               # API URL helper, Supabase client
        ├── stores/               # Pinia global stores (auth, scores)
        └── views/                # Page-level route components
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project (for auth and file storage)

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host/db   # omit for SQLite locally

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# CORS (comma-separated, required in production)
CORS_ORIGINS=https://yourdomain.com

# App
APP_ENV=development
DEBUG=true

# Score scraper polling interval (seconds)
SCORE_REFRESH_INTERVAL=60

# SMTP (contact form)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=you@gmail.com

# AI (match analysis)
OPENROUTER_API_KEY=your-key

# Stats timezone for daily resets
STATS_TIMEZONE=Europe/Rome
```

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# Apply database migrations
.venv/Scripts/alembic.exe upgrade head   # Windows
# alembic upgrade head                   # macOS / Linux

uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.  
API docs (dev only): `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

---

## API Reference

All routes are prefixed with `/api`.

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/guides` | Public | List guides (paginated, filterable) |
| `GET` | `/guides/tags` | Public | Distinct tag list |
| `GET` | `/guides/{slug}` | Public | Single guide by slug |
| `POST` | `/guides` | Admin | Create guide |
| `PUT` | `/guides/{id}` | Admin | Update guide |
| `DELETE` | `/guides/{id}` | Admin | Delete guide |
| `POST` | `/guides/images` | Admin | Upload in-content image |
| `GET` | `/outfits` | Public | List outfits (paginated) |
| `POST` | `/outfits` | Admin | Create outfit |
| `PUT` | `/outfits/{id}` | Admin | Update outfit |
| `DELETE` | `/outfits/{id}` | Admin | Delete outfit |
| `GET` | `/tour-logs` | Public | Paginated tour log history |
| `POST` | `/match-analysis` | Public | Upload `.html` log for analysis |
| `GET` | `/admin/players` | Admin | Full player list |
| `POST` | `/admin/players/aliases` | Admin | Add player alias |
| `POST` | `/contact` | Public | Send contact email |
| `WS` | `/ws/live-scores` | Public | Real-time score stream |
| `GET` | `/health` | Public | DB connectivity check |

---

## Authentication

Auth is handled by Supabase JWT:

- Frontend sends `Authorization: Bearer <token>` on every protected request
- Backend verifies the token against `SUPABASE_JWT_SECRET`
- Admin access requires `app_metadata.role == "admin"` — set server-side in Supabase only

---

## Database Migrations

```bash
# Generate a new migration from model changes
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1

# Check current schema version
alembic current
```

> Never use `Base.metadata.create_all()` for schema changes in production — Alembic only.

---

## License

MIT
