# TE4 Slam Game Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a "build your champion" simulation game at `/slam` where community members draft 9 skills from real TE4 players to create a composite player, then simulate a Grand Slam tournament bracket.

**Architecture:** Hybrid — simulation logic runs entirely in the browser (TypeScript pure functions), backend stores every run result for leaderboard + stats. Two new SQLAlchemy models (`SlamPlayer`, `SlamRun`), 10 FastAPI endpoints, Pinia store, 6 Vue components, and 1 view.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic (backend) · Vue 3 + Pinia, TypeScript, Vitest (frontend)

---

## File Map

### New files
| Path | Responsibility |
|------|---------------|
| `backend/app/models/slam.py` | ORM models + Pydantic schemas for SlamPlayer and SlamRun |
| `backend/app/api/endpoints/slam.py` | All 10 API endpoints + TOURNAMENTS config |
| `backend/tests/test_slam.py` | Schema validation unit tests |
| `frontend/src/utils/slamEngine.ts` | Pure simulation functions: OVR calc, set/match prob, tournament sim |
| `frontend/src/utils/slamEngine.test.ts` | Vitest tests for simulation engine |
| `frontend/src/stores/slam.ts` | Pinia store: state, draft logic, API calls |
| `frontend/src/components/slam/TournamentPicker.vue` | Step 1: 4 grand slam cards |
| `frontend/src/components/slam/SkillDraft.vue` | Step 2: 9-slot draft with player picker per skill |
| `frontend/src/components/slam/SimulationRound.vue` | Step 3: single round reveal (opponent + score) |
| `frontend/src/components/slam/RunResult.vue` | Step 4: champion/eliminated screen + stats |
| `frontend/src/components/slam/SlamLeaderboard.vue` | Leaderboard table + daily % stat |
| `frontend/src/views/SlamView.vue` | Top-level view orchestrating all 4 steps |

### Modified files
| Path | Change |
|------|--------|
| `backend/app/models/__init__.py` | Add slam model imports |
| `backend/app/api/router.py` | `include_router(slam.router)` |
| `frontend/src/router/index.ts` | Add `/slam` route |
| `frontend/src/App.vue` | Add TE4 Slam nav link |

---

## Task 1: Backend models + Alembic migration

**Files:**
- Create: `backend/app/models/slam.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the model file**

```python
# backend/app/models/slam.py
"""ORM models and Pydantic schemas for the TE4 Slam game."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.core.database import Base


class SlamPlayer(Base):
    __tablename__ = "slam_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    avatar_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#4CAF50")

    serve: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    # Column aliased to "return" (Python reserved word)
    return_skill: Mapped[int] = mapped_column("return", Integer, nullable=False, default=50)
    slice: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    forehand: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    backhand: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    short_accels: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    pure_defense: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    net_game: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    trickshots: Mapped[int] = mapped_column(Integer, nullable=False, default=50)


class SlamRun(Base):
    __tablename__ = "slam_runs"
    __table_args__ = (
        Index("ix_slam_runs_tournament_champion", "tournament_slug", "champion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_slug: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    build: Mapped[dict] = mapped_column(JSON, nullable=False)
    draw: Mapped[list] = mapped_column(JSON, nullable=False)
    ovr: Mapped[int] = mapped_column(Integer, nullable=False)
    round_reached: Mapped[int] = mapped_column(Integer, nullable=False)
    champion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class SlamPlayerCreate(BaseModel):
    name: str
    slug: str
    avatar_color: str = "#4CAF50"
    serve: int = Field(ge=0, le=100)
    return_skill: int = Field(ge=0, le=100)
    slice: int = Field(ge=0, le=100)
    forehand: int = Field(ge=0, le=100)
    backhand: int = Field(ge=0, le=100)
    short_accels: int = Field(ge=0, le=100)
    pure_defense: int = Field(ge=0, le=100)
    net_game: int = Field(ge=0, le=100)
    trickshots: int = Field(ge=0, le=100)


class SlamPlayerUpdate(BaseModel):
    name: str | None = None
    avatar_color: str | None = None
    serve: int | None = Field(default=None, ge=0, le=100)
    return_skill: int | None = Field(default=None, ge=0, le=100)
    slice: int | None = Field(default=None, ge=0, le=100)
    forehand: int | None = Field(default=None, ge=0, le=100)
    backhand: int | None = Field(default=None, ge=0, le=100)
    short_accels: int | None = Field(default=None, ge=0, le=100)
    pure_defense: int | None = Field(default=None, ge=0, le=100)
    net_game: int | None = Field(default=None, ge=0, le=100)
    trickshots: int | None = Field(default=None, ge=0, le=100)


class SlamPlayerResponse(SlamPlayerCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DrawRound(BaseModel):
    round: int
    opponent: str
    opp_ovr: int
    won: bool
    score: str


class SlamRunCreate(BaseModel):
    tournament_slug: str
    nickname: str
    build: dict[str, str]
    draw: list[DrawRound]
    ovr: int = Field(ge=0, le=100)
    round_reached: int = Field(ge=1, le=7)
    champion: bool


class SlamRunResponse(BaseModel):
    id: int
    tournament_slug: str
    nickname: str
    build: dict[str, Any]
    draw: list[dict[str, Any]]
    ovr: int
    round_reached: int
    champion: bool
    played_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SlamLeaderboardEntry(BaseModel):
    nickname: str
    total_runs: int
    wins: int
    best_ovr: int
    win_rate: float


class SlamStats(BaseModel):
    total_runs_today: int
    champions_today: int
    pct_champions_today: float
    total_runs_alltime: int
    total_champions_alltime: int
```

- [ ] **Step 2: Register models for Alembic detection**

Open `backend/app/models/__init__.py` and add:

```python
from app.models.slam import SlamPlayer, SlamRun  # noqa: F401
```

- [ ] **Step 3: Generate and run Alembic migration**

```bash
cd backend
.venv/Scripts/alembic.exe revision --autogenerate -m "add slam_players and slam_runs tables"
.venv/Scripts/alembic.exe upgrade head
```

Expected: migration file created in `alembic/versions/`, tables created without errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/slam.py backend/app/models/__init__.py backend/alembic/versions/
git commit -m "feat: add SlamPlayer and SlamRun models with Alembic migration"
```

---

## Task 2: Backend API endpoints + router

**Files:**
- Create: `backend/app/api/endpoints/slam.py`
- Create: `backend/tests/test_slam.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Write schema validation tests first**

```python
# backend/tests/test_slam.py
"""Schema validation tests for TE4 Slam models."""
import pytest
from pydantic import ValidationError
from app.models.slam import SlamPlayerCreate, SlamRunCreate, DrawRound


def test_slam_player_valid():
    p = SlamPlayerCreate(
        name="Jira", slug="jira",
        serve=85, return_skill=80, slice=70, forehand=90,
        backhand=75, short_accels=78, pure_defense=65,
        net_game=60, trickshots=55,
    )
    assert p.serve == 85
    assert p.return_skill == 80
    assert p.avatar_color == "#4CAF50"  # default


def test_slam_player_skill_above_100_rejected():
    with pytest.raises(ValidationError):
        SlamPlayerCreate(
            name="X", slug="x",
            serve=101, return_skill=50, slice=50, forehand=50,
            backhand=50, short_accels=50, pure_defense=50,
            net_game=50, trickshots=50,
        )


def test_slam_player_skill_below_0_rejected():
    with pytest.raises(ValidationError):
        SlamPlayerCreate(
            name="X", slug="x",
            serve=-1, return_skill=50, slice=50, forehand=50,
            backhand=50, short_accels=50, pure_defense=50,
            net_game=50, trickshots=50,
        )


def test_slam_run_valid():
    run = SlamRunCreate(
        tournament_slug="wimbledon",
        nickname="TestUser",
        build={"serve": "Jira", "return_skill": "MagRai"},
        draw=[DrawRound(round=1, opponent="MagRai", opp_ovr=78, won=True, score="3-1")],
        ovr=82,
        round_reached=1,
        champion=False,
    )
    assert run.champion is False
    assert run.ovr == 82


def test_slam_run_ovr_above_100_rejected():
    with pytest.raises(ValidationError):
        SlamRunCreate(
            tournament_slug="ao", nickname="X",
            build={}, draw=[], ovr=101, round_reached=1, champion=False,
        )
```

- [ ] **Step 2: Run tests — confirm they pass**

```bash
cd backend
python -m pytest tests/test_slam.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 3: Create the endpoints file**

```python
# backend/app/api/endpoints/slam.py
"""TE4 Slam game API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import Date, Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.limiter import limiter
from app.models.slam import (
    SlamLeaderboardEntry,
    SlamPlayer,
    SlamPlayerCreate,
    SlamPlayerResponse,
    SlamPlayerUpdate,
    SlamRun,
    SlamRunCreate,
    SlamRunResponse,
    SlamStats,
)

router = APIRouter(prefix="/slam", tags=["Slam"])

TOURNAMENTS: dict[str, dict] = {
    "ao":        {"name": "Australian Open", "surface": "hard",  "best_of": 5, "rounds": 7},
    "rg":        {"name": "Roland Garros",   "surface": "clay",  "best_of": 5, "rounds": 7},
    "wimbledon": {"name": "Wimbledon",        "surface": "grass", "best_of": 5, "rounds": 7},
    "uso":       {"name": "US Open",          "surface": "hard",  "best_of": 5, "rounds": 7},
}


# ─── Public endpoints ─────────────────────────────────────────────────────────

@router.get("/players", response_model=list[SlamPlayerResponse])
@limiter.limit("60/minute")
async def list_players(request: Request, db: AsyncSession = Depends(get_db)) -> Any:
    result = await db.execute(select(SlamPlayer).order_by(SlamPlayer.name))
    return result.scalars().all()


@router.get("/tournaments")
@limiter.limit("60/minute")
async def list_tournaments(request: Request) -> Any:
    return [{"slug": slug, **cfg} for slug, cfg in TOURNAMENTS.items()]


@router.post("/runs", response_model=SlamRunResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def submit_run(
    request: Request,
    body: SlamRunCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    if body.tournament_slug not in TOURNAMENTS:
        raise HTTPException(status_code=400, detail="Invalid tournament slug")
    nickname = body.nickname.strip()
    if not nickname:
        raise HTTPException(status_code=400, detail="Nickname is required")
    run = SlamRun(
        tournament_slug=body.tournament_slug,
        nickname=nickname[:30],
        build=body.build,
        draw=[r.model_dump() for r in body.draw],
        ovr=body.ovr,
        round_reached=body.round_reached,
        champion=body.champion,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/leaderboard/{tournament_slug}", response_model=list[SlamLeaderboardEntry])
@limiter.limit("60/minute")
async def get_leaderboard(
    request: Request,
    tournament_slug: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    if tournament_slug not in TOURNAMENTS:
        raise HTTPException(status_code=400, detail="Invalid tournament slug")
    result = await db.execute(
        select(
            SlamRun.nickname,
            func.count(SlamRun.id).label("total_runs"),
            func.sum(cast(SlamRun.champion, Integer)).label("wins"),
            func.max(SlamRun.ovr).label("best_ovr"),
        )
        .where(SlamRun.tournament_slug == tournament_slug)
        .group_by(SlamRun.nickname)
        .order_by(
            func.sum(cast(SlamRun.champion, Integer)).desc(),
            func.max(SlamRun.ovr).desc(),
        )
        .limit(50)
    )
    rows = result.all()
    return [
        SlamLeaderboardEntry(
            nickname=row.nickname,
            total_runs=row.total_runs,
            wins=row.wins or 0,
            best_ovr=row.best_ovr,
            win_rate=round((row.wins or 0) / row.total_runs * 100, 1),
        )
        for row in rows
    ]


@router.get("/stats/{tournament_slug}", response_model=SlamStats)
@limiter.limit("60/minute")
async def get_stats(
    request: Request,
    tournament_slug: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    if tournament_slug not in TOURNAMENTS:
        raise HTTPException(status_code=400, detail="Invalid tournament slug")
    today = datetime.now(timezone.utc).date()

    today_row = (await db.execute(
        select(
            func.count(SlamRun.id).label("total"),
            func.sum(cast(SlamRun.champion, Integer)).label("champs"),
        ).where(
            SlamRun.tournament_slug == tournament_slug,
            cast(SlamRun.played_at, Date) == today,
        )
    )).one()

    alltime_row = (await db.execute(
        select(
            func.count(SlamRun.id).label("total"),
            func.sum(cast(SlamRun.champion, Integer)).label("champs"),
        ).where(SlamRun.tournament_slug == tournament_slug)
    )).one()

    total_today = today_row.total or 0
    champs_today = today_row.champs or 0
    return SlamStats(
        total_runs_today=total_today,
        champions_today=champs_today,
        pct_champions_today=round(champs_today / total_today * 100, 1) if total_today else 0.0,
        total_runs_alltime=alltime_row.total or 0,
        total_champions_alltime=alltime_row.champs or 0,
    )


@router.get("/profile/{nickname}", response_model=list[SlamRunResponse])
@limiter.limit("60/minute")
async def get_profile(
    request: Request,
    nickname: str,
    tournament_slug: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    q = select(SlamRun).where(SlamRun.nickname == nickname)
    if tournament_slug:
        q = q.where(SlamRun.tournament_slug == tournament_slug)
    result = await db.execute(q.order_by(SlamRun.played_at.desc()).limit(100))
    return result.scalars().all()


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@router.post("/players", response_model=SlamPlayerResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_player(
    request: Request,
    body: SlamPlayerCreate,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    existing = (await db.execute(
        select(SlamPlayer).where(SlamPlayer.slug == body.slug)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    player = SlamPlayer(
        name=body.name, slug=body.slug, avatar_color=body.avatar_color,
        serve=body.serve, return_skill=body.return_skill, slice=body.slice,
        forehand=body.forehand, backhand=body.backhand, short_accels=body.short_accels,
        pure_defense=body.pure_defense, net_game=body.net_game, trickshots=body.trickshots,
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player


@router.put("/players/{player_id}", response_model=SlamPlayerResponse)
@limiter.limit("30/minute")
async def update_player(
    request: Request,
    player_id: int,
    body: SlamPlayerUpdate,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    player = (await db.execute(
        select(SlamPlayer).where(SlamPlayer.id == player_id)
    )).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(player, field, value)
    await db.commit()
    await db.refresh(player)
    return player


@router.delete("/players/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_player(
    request: Request,
    player_id: int,
    _admin: Any = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    player = (await db.execute(
        select(SlamPlayer).where(SlamPlayer.id == player_id)
    )).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    await db.delete(player)
    await db.commit()
```

- [ ] **Step 4: Wire into router**

Open `backend/app/api/router.py`. Add the slam import alongside the others and include the router:

```python
from app.api.endpoints import slam  # add to existing imports

# add inside the router setup block:
api_router.include_router(slam.router)
```

- [ ] **Step 5: Verify server starts**

```bash
cd backend
uvicorn app.main:app --reload 2>&1 | head -20
```

Expected: `Application startup complete.` with no import errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/endpoints/slam.py backend/app/api/router.py backend/tests/test_slam.py
git commit -m "feat: add TE4 Slam API endpoints (players, runs, leaderboard, stats)"
```

---

## Task 3: Frontend simulation engine (TDD)

**Files:**
- Create: `frontend/src/utils/slamEngine.test.ts`
- Create: `frontend/src/utils/slamEngine.ts`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/src/utils/slamEngine.test.ts
import { describe, it, expect } from 'vitest'
import {
  calcOVR, setWinProb, matchWinProb, simulateMatch, getPlayerOVR,
  SKILLS, type SkillValues,
} from './slamEngine'

const allEighty = (): SkillValues =>
  Object.fromEntries(SKILLS.map(k => [k, 80])) as SkillValues

const allEightyFive = (): SkillValues =>
  Object.fromEntries(SKILLS.map(k => [k, 85])) as SkillValues

describe('calcOVR', () => {
  it('returns same value for balanced build (lambda cancels)', () => {
    expect(calcOVR(allEighty(), 'hard')).toBe(80)
    expect(calcOVR(allEightyFive(), 'hard')).toBe(85)
  })

  it('penalizes weak-link build vs balanced build', () => {
    const broken: SkillValues = { ...allEightyFive(), trickshots: 45 }
    const balanced = allEighty()
    // broken has higher weighted avg but weak link pulls OVR down
    expect(calcOVR(broken, 'hard')).toBeLessThan(calcOVR(balanced, 'hard') + 6)
  })

  it('serve weighted higher on grass', () => {
    const serveBot: SkillValues = { ...allEighty(), serve: 95 }
    expect(calcOVR(serveBot, 'grass')).toBeGreaterThan(calcOVR(serveBot, 'clay'))
  })

  it('short_accels + pure_defense weighted higher on clay', () => {
    const defender: SkillValues = { ...allEighty(), short_accels: 95, pure_defense: 95 }
    expect(calcOVR(defender, 'clay')).toBeGreaterThan(calcOVR(defender, 'grass'))
  })
})

describe('setWinProb', () => {
  it('returns 0.5 for equal OVR', () => {
    expect(setWinProb(80, 80)).toBeCloseTo(0.5)
  })

  it('favors higher OVR player', () => {
    expect(setWinProb(85, 80)).toBeGreaterThan(0.5)
    expect(setWinProb(75, 80)).toBeLessThan(0.5)
  })

  it('approaches 1 for large advantage', () => {
    expect(setWinProb(99, 40)).toBeGreaterThan(0.99)
  })
})

describe('matchWinProb', () => {
  it('amplifies advantage in best-of-5 vs single set', () => {
    const p = setWinProb(85, 80) // ~0.57
    expect(matchWinProb(p, 5)).toBeGreaterThan(p)
  })

  it('returns ~1 for p=1', () => {
    expect(matchWinProb(1, 5)).toBeCloseTo(1)
    expect(matchWinProb(1, 3)).toBeCloseTo(1)
  })

  it('returns ~0 for p=0', () => {
    expect(matchWinProb(0, 5)).toBeCloseTo(0)
    expect(matchWinProb(0, 3)).toBeCloseTo(0)
  })

  it('best-of-5 is harder to win than best-of-3 for underdog', () => {
    const p = 0.45 // slight underdog
    expect(matchWinProb(p, 5)).toBeLessThan(matchWinProb(p, 3))
  })
})

describe('simulateMatch', () => {
  it('returns won (bool) and score (N-M format)', () => {
    const result = simulateMatch(80, 80, 5)
    expect(typeof result.won).toBe('boolean')
    expect(result.score).toMatch(/^\d-\d$/)
  })

  it('dominant player wins vast majority over 1000 runs', () => {
    let wins = 0
    for (let i = 0; i < 1000; i++) {
      if (simulateMatch(99, 40, 5).won) wins++
    }
    expect(wins).toBeGreaterThan(950)
  })

  it('score sets sum to bestOf in a 3-set match for bo5', () => {
    // bo5 needs 3 sets to win; loser has 0 or 1 or 2
    const { score } = simulateMatch(80, 80, 5)
    const [w, l] = score.split('-').map(Number)
    expect(w).toBe(3)
    expect(l).toBeGreaterThanOrEqual(0)
    expect(l).toBeLessThanOrEqual(2)
  })
})
```

- [ ] **Step 2: Run tests — confirm they fail (module not found)**

```bash
cd frontend
npm run test -- slamEngine --run 2>&1 | head -20
```

Expected: `Cannot find module './slamEngine'`

- [ ] **Step 3: Implement the simulation engine**

```typescript
// frontend/src/utils/slamEngine.ts
export const SKILLS = [
  'serve', 'return_skill', 'slice', 'forehand', 'backhand',
  'short_accels', 'pure_defense', 'net_game', 'trickshots',
] as const

export type SkillKey = typeof SKILLS[number]
export type SkillValues = Record<SkillKey, number>

export const SKILL_LABELS: Record<SkillKey, string> = {
  serve: 'Serve',
  return_skill: 'Return',
  slice: 'Slice',
  forehand: 'Forehand',
  backhand: 'Backhand',
  short_accels: 'Short Accels',
  pure_defense: 'Pure Defense',
  net_game: 'Net Game',
  trickshots: 'Trickshots',
}

const WEIGHTS_BASE: Record<SkillKey, number> = {
  serve: 1.4,
  return_skill: 1.3,
  forehand: 1.3,
  backhand: 1.1,
  short_accels: 1.2,
  pure_defense: 1.0,
  net_game: 0.7,
  trickshots: 0.7,
  slice: 1.0,
}

const SURFACE_OVERRIDES: Record<string, Partial<Record<SkillKey, number>>> = {
  grass: { serve: 1.7, net_game: 1.0, return_skill: 1.1 },
  clay:  { short_accels: 1.6, pure_defense: 1.4, serve: 0.9 },
  hard:  {},
}

function getWeights(surface: string): Record<SkillKey, number> {
  return { ...WEIGHTS_BASE, ...(SURFACE_OVERRIDES[surface] ?? {}) }
}

export function calcOVR(skills: SkillValues, surface: string, lambda = 0.2): number {
  const weights = getWeights(surface)
  const sumW = SKILLS.reduce((s, k) => s + weights[k], 0)
  const weighted = SKILLS.reduce((s, k) => s + weights[k] * skills[k], 0) / sumW
  const worst = Math.min(...SKILLS.map(k => skills[k]))
  return Math.round((1 - lambda) * weighted + lambda * worst)
}

export interface SlamPlayerData {
  id: number
  name: string
  slug: string
  avatar_color: string
  serve: number
  return_skill: number
  slice: number
  forehand: number
  backhand: number
  short_accels: number
  pure_defense: number
  net_game: number
  trickshots: number
}

export function getPlayerSkills(player: SlamPlayerData): SkillValues {
  return Object.fromEntries(SKILLS.map(k => [k, player[k]])) as SkillValues
}

export function getPlayerOVR(player: SlamPlayerData, surface: string): number {
  return calcOVR(getPlayerSkills(player), surface)
}

export function setWinProb(myOVR: number, oppOVR: number, scale = 40): number {
  return 1 / (1 + Math.pow(10, (oppOVR - myOVR) / scale))
}

export function matchWinProb(p: number, bestOf: number): number {
  const q = 1 - p
  if (bestOf === 5) return p ** 3 * (1 + 3 * q + 6 * q * q)
  if (bestOf === 3) return p ** 2 * (1 + 2 * q)
  return p
}

export function simulateMatch(
  myOVR: number,
  oppOVR: number,
  bestOf: number,
): { won: boolean; score: string } {
  const p = setWinProb(myOVR, oppOVR)
  const needed = Math.ceil(bestOf / 2)
  let me = 0, opp = 0
  while (me < needed && opp < needed) {
    Math.random() < p ? me++ : opp++
  }
  return { won: me === needed, score: `${me}-${opp}` }
}

export interface DrawRound {
  round: number
  opponent: string
  opp_ovr: number
  won: boolean
  score: string
}

export function drawOpponents(
  players: SlamPlayerData[],
  rounds: number,
  surface: string,
): SlamPlayerData[] {
  const shuffled = [...players].sort(() => Math.random() - 0.5)
  const selected = shuffled.slice(0, rounds)
  // Sort ascending by OVR so early rounds are easier
  return selected.sort((a, b) => getPlayerOVR(a, surface) - getPlayerOVR(b, surface))
}

export function simulateTournament(
  mySkills: SkillValues,
  opponents: SlamPlayerData[],
  surface: string,
  bestOf: number,
): DrawRound[] {
  const myOVR = calcOVR(mySkills, surface)
  const draw: DrawRound[] = []
  for (let r = 0; r < opponents.length; r++) {
    const opp = opponents[r]
    const oppOVR = getPlayerOVR(opp, surface)
    const result = simulateMatch(myOVR, oppOVR, bestOf)
    draw.push({ round: r + 1, opponent: opp.name, opp_ovr: oppOVR, ...result })
    if (!result.won) break
  }
  return draw
}
```

- [ ] **Step 4: Run tests — all must pass**

```bash
cd frontend
npm run test -- slamEngine --run
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/slamEngine.ts frontend/src/utils/slamEngine.test.ts
git commit -m "feat: add TE4 Slam simulation engine with full test coverage"
```

---

## Task 4: Pinia store

**Files:**
- Create: `frontend/src/stores/slam.ts`

- [ ] **Step 1: Create the store**

```typescript
// frontend/src/stores/slam.ts
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { apiUrl } from '@/config/api'
import {
  SKILLS, calcOVR, drawOpponents, getPlayerSkills, simulateTournament,
  type DrawRound, type SkillKey, type SkillValues, type SlamPlayerData,
} from '@/utils/slamEngine'

export interface Tournament {
  slug: string
  name: string
  surface: string
  best_of: number
  rounds: number
}

export interface SlamLeaderboardEntry {
  nickname: string
  total_runs: number
  wins: number
  best_ovr: number
  win_rate: number
}

export interface SlamStats {
  total_runs_today: number
  champions_today: number
  pct_champions_today: number
  total_runs_alltime: number
  total_champions_alltime: number
}

export const useSlamStore = defineStore('slam', () => {
  const players = ref<SlamPlayerData[]>([])
  const tournaments = ref<Tournament[]>([])
  const activeTournament = ref<Tournament | null>(null)
  const draft = ref<Partial<Record<SkillKey, string>>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)
  const leaderboard = ref<SlamLeaderboardEntry[]>([])
  const stats = ref<SlamStats | null>(null)

  const isDraftComplete = computed(() => SKILLS.every(k => draft.value[k]))

  const usedPlayers = computed(() => new Set(Object.values(draft.value).filter(Boolean)))

  const mySkills = computed((): SkillValues | null => {
    if (!isDraftComplete.value || !activeTournament.value) return null
    const result = {} as SkillValues
    for (const skill of SKILLS) {
      const playerName = draft.value[skill]!
      const player = players.value.find(p => p.name === playerName)
      if (!player) return null
      result[skill] = player[skill]
    }
    return result
  })

  const myOVR = computed(() => {
    if (!mySkills.value || !activeTournament.value) return 0
    return calcOVR(mySkills.value, activeTournament.value.surface)
  })

  async function fetchPlayers(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(apiUrl('/api/slam/players'))
      if (!res.ok) throw new Error('Failed to load players')
      players.value = await res.json()
    } catch (err: any) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTournaments(): Promise<void> {
    try {
      const res = await fetch(apiUrl('/api/slam/tournaments'))
      if (!res.ok) return
      tournaments.value = await res.json()
    } catch {
      // silently fail — tournaments are config, not dynamic
    }
  }

  function selectTournament(slug: string): void {
    activeTournament.value = tournaments.value.find(t => t.slug === slug) ?? null
    draft.value = {}
  }

  function pickSkill(skill: SkillKey, playerName: string): void {
    // Free previous slot if this player was already drafted elsewhere
    for (const [k, v] of Object.entries(draft.value) as [SkillKey, string][]) {
      if (v === playerName && k !== skill) {
        delete draft.value[k]
      }
    }
    draft.value[skill] = playerName
  }

  function clearSkill(skill: SkillKey): void {
    delete draft.value[skill]
  }

  function resetDraft(): void {
    draft.value = {}
  }

  function runSimulation(): DrawRound[] | null {
    if (!mySkills.value || !activeTournament.value) return null
    const opponents = drawOpponents(
      players.value,
      activeTournament.value.rounds,
      activeTournament.value.surface,
    )
    return simulateTournament(
      mySkills.value,
      opponents,
      activeTournament.value.surface,
      activeTournament.value.best_of,
    )
  }

  async function submitRun(nickname: string, draw: DrawRound[]): Promise<void> {
    if (!activeTournament.value || !isDraftComplete.value) return
    const roundReached = draw.length
    const champion = draw[draw.length - 1]?.won ?? false
    const res = await fetch(apiUrl('/api/slam/runs'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tournament_slug: activeTournament.value.slug,
        nickname: nickname.trim(),
        build: draft.value,
        draw,
        ovr: myOVR.value,
        round_reached: roundReached,
        champion,
      }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Failed to submit run')
    }
  }

  async function fetchLeaderboard(tournamentSlug: string): Promise<void> {
    try {
      const res = await fetch(apiUrl(`/api/slam/leaderboard/${tournamentSlug}`))
      if (!res.ok) return
      leaderboard.value = await res.json()
    } catch { /* ignore */ }
  }

  async function fetchStats(tournamentSlug: string): Promise<void> {
    try {
      const res = await fetch(apiUrl(`/api/slam/stats/${tournamentSlug}`))
      if (!res.ok) return
      stats.value = await res.json()
    } catch { /* ignore */ }
  }

  return {
    players, tournaments, activeTournament, draft, loading, error,
    leaderboard, stats, isDraftComplete, usedPlayers, mySkills, myOVR,
    fetchPlayers, fetchTournaments, selectTournament,
    pickSkill, clearSkill, resetDraft,
    runSimulation, submitRun, fetchLeaderboard, fetchStats,
  }
})
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/slam.ts
git commit -m "feat: add Slam Pinia store with draft logic and API calls"
```

---

## Task 5: TournamentPicker.vue

**Files:**
- Create: `frontend/src/components/slam/TournamentPicker.vue`

- [ ] **Step 1: Create the component**

```vue
<!-- frontend/src/components/slam/TournamentPicker.vue -->
<script setup lang="ts">
import type { Tournament } from '@/stores/slam'

defineProps<{ tournaments: Tournament[] }>()
const emit = defineEmits<{ select: [slug: string] }>()

const SURFACE_EMOJI: Record<string, string> = {
  hard: '🔵', clay: '🟠', grass: '🟢',
}

const BOOSTED_SKILLS: Record<string, string> = {
  grass: 'Serve · Net Game',
  clay: 'Short Accels · Pure Defense',
  hard: 'Balanced',
}
</script>

<template>
  <div class="tournament-picker">
    <h2 class="picker-title">Choose your Grand Slam</h2>
    <p class="picker-sub">Each surface rewards different skills in your build.</p>
    <div class="cards">
      <button
        v-for="t in tournaments"
        :key="t.slug"
        class="slam-card"
        :class="`surface-${t.surface}`"
        @click="emit('select', t.slug)"
      >
        <span class="surface-dot">{{ SURFACE_EMOJI[t.surface] }}</span>
        <span class="slam-name">{{ t.name }}</span>
        <span class="slam-format">Best of {{ t.best_of }} · {{ t.rounds }} rounds</span>
        <span class="slam-boost">↑ {{ BOOSTED_SKILLS[t.surface] }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.tournament-picker { text-align: center; padding: var(--space-6) 0; }
.picker-title { font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); margin-bottom: var(--space-2); }
.picker-sub { color: var(--color-text-muted); margin-bottom: var(--space-6); }
.cards { display: flex; gap: var(--space-4); justify-content: center; flex-wrap: wrap; }
.slam-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-6) var(--space-5); min-width: 160px;
  background: var(--color-surface); border: 2px solid var(--color-border);
  border-radius: var(--radius-lg); cursor: pointer;
  transition: border-color var(--transition-fast), transform var(--transition-fast);
}
.slam-card:hover { transform: translateY(-3px); border-color: var(--color-accent); }
.slam-card.surface-grass:hover { border-color: #4caf50; }
.slam-card.surface-clay:hover { border-color: #e65100; }
.slam-card.surface-hard:hover { border-color: #1565c0; }
.surface-dot { font-size: 2rem; }
.slam-name { font-size: var(--font-size-lg); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }
.slam-format { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.slam-boost { font-size: var(--font-size-xs); color: var(--color-accent); font-weight: var(--font-weight-semibold); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/slam/TournamentPicker.vue
git commit -m "feat: add TournamentPicker component"
```

---

## Task 6: SkillDraft.vue

**Files:**
- Create: `frontend/src/components/slam/SkillDraft.vue`

- [ ] **Step 1: Create the component**

```vue
<!-- frontend/src/components/slam/SkillDraft.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { SKILLS, SKILL_LABELS, type SkillKey, type SlamPlayerData } from '@/utils/slamEngine'

const props = defineProps<{
  players: SlamPlayerData[]
  draft: Partial<Record<SkillKey, string>>
  usedPlayers: Set<string>
  myOVR: number
  isDraftComplete: boolean
  surface: string
}>()

const emit = defineEmits<{
  pick: [skill: SkillKey, playerName: string]
  clear: [skill: SkillKey]
  simulate: []
}>()

const openSlot = ref<SkillKey | null>(null)

function togglePicker(skill: SkillKey) {
  openSlot.value = openSlot.value === skill ? null : skill
}

function pick(skill: SkillKey, player: SlamPlayerData) {
  emit('pick', skill, player.name)
  openSlot.value = null
}

function sortedPlayers(skill: SkillKey) {
  return [...props.players].sort((a, b) => b[skill] - a[skill])
}

function isAvailable(player: SlamPlayerData, skill: SkillKey) {
  // A player is unavailable if already used for a DIFFERENT skill
  return !props.usedPlayers.has(player.name) || props.draft[skill] === player.name
}

const draftedCount = computed(() => SKILLS.filter(k => props.draft[k]).length)

const ROUND_LABELS = ['R1', 'R2', 'R3', 'QF', 'SF', 'F', 'W']
</script>

<template>
  <div class="skill-draft">
    <div class="draft-header">
      <div>
        <h2 class="draft-title">Build your champion</h2>
        <p class="draft-sub">Pick one player per skill — each player can only contribute once.</p>
      </div>
      <div class="ovr-badge" :class="{ ready: isDraftComplete }">
        OVR {{ isDraftComplete ? myOVR : `${draftedCount}/9` }}
      </div>
    </div>

    <div class="slots">
      <div v-for="skill in SKILLS" :key="skill" class="slot">
        <div class="slot-label">{{ SKILL_LABELS[skill] }}</div>

        <button
          class="slot-btn"
          :class="{ filled: !!draft[skill], open: openSlot === skill }"
          @click="togglePicker(skill)"
        >
          <template v-if="draft[skill]">
            <span
              class="player-chip"
              :style="{ background: players.find(p => p.name === draft[skill])?.avatar_color ?? '#666' }"
            >{{ draft[skill]![0] }}</span>
            <span class="player-name">{{ draft[skill] }}</span>
            <span class="skill-val">{{ players.find(p => p.name === draft[skill])?.[skill] }}</span>
          </template>
          <span v-else class="placeholder">Pick a player…</span>
        </button>

        <button v-if="draft[skill]" class="clear-btn" @click.stop="emit('clear', skill)" title="Remove">×</button>

        <!-- Player picker dropdown -->
        <div v-if="openSlot === skill" class="picker-dropdown">
          <div
            v-for="player in sortedPlayers(skill)"
            :key="player.id"
            class="picker-row"
            :class="{ disabled: !isAvailable(player, skill) }"
            @click="isAvailable(player, skill) ? pick(skill, player) : undefined"
          >
            <span
              class="player-chip"
              :style="{ background: player.avatar_color }"
            >{{ player.name[0] }}</span>
            <span class="picker-name">{{ player.name }}</span>
            <span class="picker-val">{{ player[skill] }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="draft-actions">
      <button
        class="btn-simulate"
        :disabled="!isDraftComplete"
        @click="emit('simulate')"
      >
        {{ isDraftComplete ? '▶ Simulate Tournament' : `Fill all 9 skills (${draftedCount}/9)` }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.skill-draft { padding: var(--space-4) 0; }
.draft-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--space-5); }
.draft-title { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); margin-bottom: var(--space-1); }
.draft-sub { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.ovr-badge {
  background: var(--color-surface); border: 2px solid var(--color-border);
  border-radius: var(--radius-lg); padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-lg); font-weight: var(--font-weight-bold); color: var(--color-text-muted);
  transition: all var(--transition-fast);
}
.ovr-badge.ready { border-color: var(--color-accent); color: var(--color-accent); }

.slots { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-3); }
.slot { position: relative; }
.slot-label { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); text-transform: uppercase; letter-spacing: 1px; color: var(--color-text-muted); margin-bottom: var(--space-1); }
.slot-btn {
  width: 100%; display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); background: var(--color-surface);
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
  cursor: pointer; transition: border-color var(--transition-fast);
  min-height: 44px;
}
.slot-btn:hover, .slot-btn.open { border-color: var(--color-accent); }
.slot-btn.filled { border-color: var(--color-border-hover); }
.placeholder { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.player-chip {
  width: 26px; height: 26px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center;
  font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); color: white;
  flex-shrink: 0;
}
.player-name { flex: 1; font-size: var(--font-size-sm); color: var(--color-text-primary); text-align: left; }
.skill-val { font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); color: var(--color-accent); font-family: var(--font-mono); }
.clear-btn {
  position: absolute; right: -10px; top: 50%; transform: translateY(-50%) translateY(10px);
  width: 20px; height: 20px; border-radius: 50%; border: none;
  background: var(--color-text-muted); color: var(--color-bg); cursor: pointer;
  font-size: 12px; line-height: 1; display: flex; align-items: center; justify-content: center;
}

.picker-dropdown {
  position: absolute; left: 0; right: 0; top: calc(100% + 4px); z-index: 100;
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: var(--radius-md); box-shadow: var(--shadow-lg);
  max-height: 240px; overflow-y: auto;
}
.picker-row {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); cursor: pointer;
  transition: background var(--transition-fast);
}
.picker-row:hover:not(.disabled) { background: var(--color-bg-hover); }
.picker-row.disabled { opacity: 0.35; cursor: not-allowed; }
.picker-name { flex: 1; font-size: var(--font-size-sm); }
.picker-val { font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); color: var(--color-accent); font-family: var(--font-mono); }

.draft-actions { margin-top: var(--space-6); display: flex; justify-content: center; }
.btn-simulate {
  padding: var(--space-3) var(--space-8); background: var(--color-accent); color: white;
  border: none; border-radius: var(--radius-lg); font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold); cursor: pointer; transition: opacity var(--transition-fast);
}
.btn-simulate:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-simulate:not(:disabled):hover { opacity: 0.85; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/slam/SkillDraft.vue
git commit -m "feat: add SkillDraft component with draft mode picker"
```

---

## Task 7: SimulationRound.vue + RunResult.vue + SlamLeaderboard.vue

**Files:**
- Create: `frontend/src/components/slam/SimulationRound.vue`
- Create: `frontend/src/components/slam/RunResult.vue`
- Create: `frontend/src/components/slam/SlamLeaderboard.vue`

- [ ] **Step 1: Create SimulationRound.vue**

```vue
<!-- frontend/src/components/slam/SimulationRound.vue -->
<script setup lang="ts">
import type { DrawRound } from '@/utils/slamEngine'

const props = defineProps<{
  round: DrawRound
  roundLabel: string
  isLast: boolean
}>()

const emit = defineEmits<{ next: [] }>()
</script>

<template>
  <div class="sim-round" :class="{ won: round.won, lost: !round.won }">
    <div class="round-badge">{{ roundLabel }}</div>

    <div class="matchup">
      <div class="player-side you">
        <span class="player-label">YOU</span>
      </div>
      <div class="score-center">
        <span class="score">{{ round.score }}</span>
        <span class="vs-text">sets</span>
      </div>
      <div class="player-side opp">
        <span class="player-label">{{ round.opponent }}</span>
        <span class="opp-ovr">OVR {{ round.opp_ovr }}</span>
      </div>
    </div>

    <div class="result-banner" :class="{ won: round.won, lost: !round.won }">
      {{ round.won ? '✓ Victory' : '✗ Eliminated' }}
    </div>

    <button class="next-btn" @click="emit('next')">
      {{ round.won && !isLast ? 'Next Round →' : 'See Results' }}
    </button>
  </div>
</template>

<style scoped>
.sim-round {
  max-width: 420px; margin: 0 auto; padding: var(--space-6);
  background: var(--color-surface); border: 2px solid var(--color-border);
  border-radius: var(--radius-xl); text-align: center;
  transition: border-color var(--transition-fast);
}
.sim-round.won { border-color: #4caf50; }
.sim-round.lost { border-color: #e53935; }

.round-badge {
  display: inline-block; padding: var(--space-1) var(--space-3);
  background: var(--color-bg-secondary); border-radius: var(--radius-full);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-bold);
  text-transform: uppercase; letter-spacing: 1px; color: var(--color-text-muted);
  margin-bottom: var(--space-5);
}

.matchup { display: flex; align-items: center; justify-content: center; gap: var(--space-4); margin-bottom: var(--space-5); }
.player-side { display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 100px; }
.player-label { font-size: var(--font-size-base); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }
.opp-ovr { font-size: var(--font-size-xs); color: var(--color-text-muted); font-family: var(--font-mono); }
.score-center { display: flex; flex-direction: column; align-items: center; }
.score { font-size: 2.5rem; font-weight: var(--font-weight-bold); font-family: var(--font-mono); color: var(--color-text-primary); }
.vs-text { font-size: var(--font-size-xs); color: var(--color-text-muted); }

.result-banner {
  padding: var(--space-2) var(--space-4); border-radius: var(--radius-md);
  font-weight: var(--font-weight-bold); font-size: var(--font-size-lg);
  margin-bottom: var(--space-5);
}
.result-banner.won { background: rgba(76, 175, 80, 0.15); color: #4caf50; }
.result-banner.lost { background: rgba(229, 57, 53, 0.15); color: #e53935; }

.next-btn {
  padding: var(--space-2) var(--space-6); background: var(--color-accent); color: white;
  border: none; border-radius: var(--radius-md); font-weight: var(--font-weight-semibold);
  cursor: pointer; transition: opacity var(--transition-fast);
}
.next-btn:hover { opacity: 0.85; }
</style>
```

- [ ] **Step 2: Create RunResult.vue**

```vue
<!-- frontend/src/components/slam/RunResult.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import type { DrawRound } from '@/utils/slamEngine'
import type { SlamStats } from '@/stores/slam'

const props = defineProps<{
  draw: DrawRound[]
  ovr: number
  tournamentName: string
  stats: SlamStats | null
  submitting: boolean
}>()

const emit = defineEmits<{
  submit: [nickname: string]
  playAgain: []
  changeTournament: []
}>()

const champion = props.draw[props.draw.length - 1]?.won ?? false
const roundReached = props.draw.length

const ROUND_LABELS: Record<number, string> = { 1: 'R1', 2: 'R2', 3: 'R3', 4: 'QF', 5: 'SF', 6: 'F', 7: 'W' }

const nickname = ref(localStorage.getItem('slam_nickname') || '')
const submitted = ref(false)
const submitError = ref('')

async function handleSubmit() {
  if (!nickname.value.trim()) { submitError.value = 'Enter a nickname'; return }
  submitError.value = ''
  localStorage.setItem('slam_nickname', nickname.value.trim())
  emit('submit', nickname.value.trim())
  submitted.value = true
}
</script>

<template>
  <div class="run-result">
    <!-- Champion or eliminated header -->
    <div class="result-hero" :class="{ champion, eliminated: !champion }">
      <span class="result-trophy">{{ champion ? '🏆' : '💥' }}</span>
      <h2 class="result-heading">
        {{ champion ? `${tournamentName} Champion!` : `Eliminated in ${ROUND_LABELS[roundReached]}` }}
      </h2>
      <p class="result-ovr">Your OVR: <strong>{{ ovr }}</strong></p>
    </div>

    <!-- Match history -->
    <div class="draw-history">
      <h3 class="section-title">Your Run</h3>
      <div v-for="r in draw" :key="r.round" class="draw-row" :class="{ won: r.won, lost: !r.won }">
        <span class="draw-round">{{ ROUND_LABELS[r.round] }}</span>
        <span class="draw-opp">vs {{ r.opponent }} ({{ r.opp_ovr }})</span>
        <span class="draw-score">{{ r.score }}</span>
        <span class="draw-result">{{ r.won ? '✓' : '✗' }}</span>
      </div>
    </div>

    <!-- Global stats -->
    <div v-if="stats" class="global-stats">
      <div class="stat">
        <span class="stat-val">{{ stats.pct_champions_today }}%</span>
        <span class="stat-label">won today</span>
      </div>
      <div class="stat">
        <span class="stat-val">{{ stats.total_runs_today }}</span>
        <span class="stat-label">runs today</span>
      </div>
      <div class="stat">
        <span class="stat-val">{{ stats.total_champions_alltime }}</span>
        <span class="stat-label">all-time champs</span>
      </div>
    </div>

    <!-- Submit run -->
    <div v-if="!submitted" class="submit-area">
      <p class="submit-label">Save your run to the leaderboard</p>
      <div class="submit-row">
        <input
          v-model="nickname"
          class="nick-input"
          placeholder="Your nickname"
          maxlength="30"
          @keyup.enter="handleSubmit"
        />
        <button class="btn-submit" :disabled="submitting" @click="handleSubmit">
          {{ submitting ? '…' : 'Save' }}
        </button>
      </div>
      <p v-if="submitError" class="submit-error">{{ submitError }}</p>
    </div>
    <p v-else class="submitted-msg">✓ Run saved!</p>

    <!-- Actions -->
    <div class="result-actions">
      <button class="btn-secondary" @click="emit('playAgain')">Play Again</button>
      <button class="btn-secondary" @click="emit('changeTournament')">Change Slam</button>
    </div>
  </div>
</template>

<style scoped>
.run-result { max-width: 500px; margin: 0 auto; display: flex; flex-direction: column; gap: var(--space-5); }
.result-hero { text-align: center; padding: var(--space-6); border-radius: var(--radius-xl); }
.result-hero.champion { background: rgba(76, 175, 80, 0.1); border: 2px solid #4caf50; }
.result-hero.eliminated { background: rgba(229, 57, 53, 0.08); border: 2px solid var(--color-border); }
.result-trophy { font-size: 3rem; display: block; margin-bottom: var(--space-2); }
.result-heading { font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); margin-bottom: var(--space-1); }
.result-ovr { color: var(--color-text-muted); }

.section-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); text-transform: uppercase; letter-spacing: 1px; color: var(--color-text-muted); margin-bottom: var(--space-2); }
.draw-history { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); overflow: hidden; }
.draw-row { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--color-border); }
.draw-row:last-child { border-bottom: none; }
.draw-round { font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); text-transform: uppercase; color: var(--color-text-muted); min-width: 28px; }
.draw-opp { flex: 1; font-size: var(--font-size-sm); }
.draw-score { font-family: var(--font-mono); font-size: var(--font-size-sm); color: var(--color-text-muted); }
.draw-result { font-weight: var(--font-weight-bold); }
.draw-row.won .draw-result { color: #4caf50; }
.draw-row.lost .draw-result { color: #e53935; }

.global-stats { display: flex; justify-content: center; gap: var(--space-6); }
.stat { display: flex; flex-direction: column; align-items: center; }
.stat-val { font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); color: var(--color-accent); }
.stat-label { font-size: var(--font-size-xs); color: var(--color-text-muted); }

.submit-area { display: flex; flex-direction: column; gap: var(--space-2); }
.submit-label { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.submit-row { display: flex; gap: var(--space-2); }
.nick-input {
  flex: 1; background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: var(--radius-md); padding: var(--space-2) var(--space-3);
  color: var(--color-text-primary); font-size: var(--font-size-sm);
}
.nick-input:focus { outline: none; border-color: var(--color-accent); }
.btn-submit {
  padding: var(--space-2) var(--space-4); background: var(--color-accent); color: white;
  border: none; border-radius: var(--radius-md); font-weight: var(--font-weight-semibold); cursor: pointer;
}
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
.submit-error { color: #e53935; font-size: var(--font-size-xs); }
.submitted-msg { color: #4caf50; font-weight: var(--font-weight-semibold); text-align: center; }

.result-actions { display: flex; justify-content: center; gap: var(--space-3); }
.btn-secondary {
  padding: var(--space-2) var(--space-5); background: transparent;
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
  color: var(--color-text-secondary); cursor: pointer; transition: border-color var(--transition-fast);
}
.btn-secondary:hover { border-color: var(--color-accent); color: var(--color-text-primary); }
</style>
```

- [ ] **Step 3: Create SlamLeaderboard.vue**

```vue
<!-- frontend/src/components/slam/SlamLeaderboard.vue -->
<script setup lang="ts">
import type { SlamLeaderboardEntry } from '@/stores/slam'

defineProps<{ entries: SlamLeaderboardEntry[] }>()
</script>

<template>
  <div class="leaderboard">
    <h3 class="lb-title">All-Time Leaderboard</h3>
    <table class="lb-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Nickname</th>
          <th>Wins</th>
          <th>Runs</th>
          <th>Win %</th>
          <th>Best OVR</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(entry, i) in entries" :key="entry.nickname">
          <td class="rank">{{ i + 1 }}</td>
          <td class="nick">{{ entry.nickname }}</td>
          <td class="wins">{{ entry.wins }}</td>
          <td class="runs">{{ entry.total_runs }}</td>
          <td class="rate">{{ entry.win_rate }}%</td>
          <td class="ovr">{{ entry.best_ovr }}</td>
        </tr>
        <tr v-if="!entries.length">
          <td colspan="6" class="empty">No runs yet. Be the first!</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.leaderboard { }
.lb-title { font-size: var(--font-size-base); font-weight: var(--font-weight-bold); text-transform: uppercase; letter-spacing: 1px; color: var(--color-text-muted); margin-bottom: var(--space-3); }
.lb-table { width: 100%; border-collapse: collapse; }
.lb-table th {
  text-align: left; font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold);
  text-transform: uppercase; letter-spacing: 1px; color: var(--color-text-muted);
  padding: var(--space-1) var(--space-2); border-bottom: 1px solid var(--color-border);
}
.lb-table td { padding: var(--space-2); font-size: var(--font-size-sm); border-bottom: 1px solid var(--color-border); }
.rank { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.nick { font-weight: var(--font-weight-semibold); color: var(--color-text-primary); }
.wins { color: #4caf50; font-weight: var(--font-weight-bold); }
.rate { font-family: var(--font-mono); }
.ovr { font-family: var(--font-mono); color: var(--color-accent); }
.empty { text-align: center; color: var(--color-text-muted); padding: var(--space-6); }
</style>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/slam/SimulationRound.vue frontend/src/components/slam/RunResult.vue frontend/src/components/slam/SlamLeaderboard.vue
git commit -m "feat: add SimulationRound, RunResult, and SlamLeaderboard components"
```

---

## Task 8: SlamView.vue

**Files:**
- Create: `frontend/src/views/SlamView.vue`

- [ ] **Step 1: Create the view**

```vue
<!-- frontend/src/views/SlamView.vue -->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useSlamStore } from '@/stores/slam'
import TournamentPicker from '@/components/slam/TournamentPicker.vue'
import SkillDraft from '@/components/slam/SkillDraft.vue'
import SimulationRound from '@/components/slam/SimulationRound.vue'
import RunResult from '@/components/slam/RunResult.vue'
import SlamLeaderboard from '@/components/slam/SlamLeaderboard.vue'
import type { DrawRound } from '@/utils/slamEngine'

type Step = 'tournament' | 'draft' | 'simulation' | 'result'

const store = useSlamStore()
const step = ref<Step>('tournament')
const simulationDraw = ref<DrawRound[]>([])
const revealedRound = ref(0)
const submitting = ref(false)

const ROUND_LABELS: Record<number, string> = { 1: 'R1', 2: 'R2', 3: 'R3', 4: 'QF', 5: 'SF', 6: 'F', 7: 'Final' }

onMounted(async () => {
  await Promise.all([store.fetchPlayers(), store.fetchTournaments()])
})

function selectTournament(slug: string) {
  store.selectTournament(slug)
  step.value = 'draft'
}

function startSimulation() {
  const draw = store.runSimulation()
  if (!draw) return
  simulationDraw.value = draw
  revealedRound.value = 0
  step.value = 'simulation'
}

function nextRound() {
  if (revealedRound.value < simulationDraw.value.length - 1) {
    revealedRound.value++
  } else {
    // Load stats and leaderboard before showing result
    const slug = store.activeTournament!.slug
    store.fetchStats(slug)
    store.fetchLeaderboard(slug)
    step.value = 'result'
  }
}

async function handleSubmit(nickname: string) {
  submitting.value = true
  try {
    await store.submitRun(nickname, simulationDraw.value)
    await store.fetchLeaderboard(store.activeTournament!.slug)
  } catch {
    // error shown by RunResult
  } finally {
    submitting.value = false
  }
}

function playAgain() {
  store.resetDraft()
  simulationDraw.value = []
  revealedRound.value = 0
  step.value = 'draft'
}

function changeTournament() {
  store.resetDraft()
  simulationDraw.value = []
  revealedRound.value = 0
  step.value = 'tournament'
}
</script>

<template>
  <main class="slam-view">
    <div class="slam-header">
      <h1 class="slam-title">TE4 Slam</h1>
      <p class="slam-desc">Build your champion from community players. Simulate the Grand Slam.</p>

      <!-- Step breadcrumb -->
      <div class="steps">
        <span :class="{ active: step === 'tournament', done: step !== 'tournament' }">1. Choose Slam</span>
        <span class="step-sep">›</span>
        <span :class="{ active: step === 'draft', done: ['simulation','result'].includes(step) }">2. Draft Build</span>
        <span class="step-sep">›</span>
        <span :class="{ active: step === 'simulation' || step === 'result' }">3. Simulate</span>
      </div>
    </div>

    <div class="slam-body">
      <!-- Step 1: Tournament Picker -->
      <TournamentPicker
        v-if="step === 'tournament'"
        :tournaments="store.tournaments"
        @select="selectTournament"
      />

      <!-- Step 2: Skill Draft -->
      <SkillDraft
        v-else-if="step === 'draft'"
        :players="store.players"
        :draft="store.draft"
        :used-players="store.usedPlayers"
        :my-o-v-r="store.myOVR"
        :is-draft-complete="store.isDraftComplete"
        :surface="store.activeTournament?.surface ?? 'hard'"
        @pick="store.pickSkill"
        @clear="store.clearSkill"
        @simulate="startSimulation"
      />

      <!-- Step 3: Round-by-round simulation -->
      <div v-else-if="step === 'simulation'" class="simulation-wrap">
        <div class="sim-progress">
          Round {{ revealedRound + 1 }} of {{ simulationDraw.length }}
        </div>
        <SimulationRound
          :round="simulationDraw[revealedRound]"
          :round-label="ROUND_LABELS[simulationDraw[revealedRound].round] ?? `R${simulationDraw[revealedRound].round}`"
          :is-last="revealedRound === simulationDraw.length - 1"
          @next="nextRound"
        />
      </div>

      <!-- Step 4: Result -->
      <div v-else-if="step === 'result'" class="result-wrap">
        <RunResult
          :draw="simulationDraw"
          :ovr="store.myOVR"
          :tournament-name="store.activeTournament?.name ?? ''"
          :stats="store.stats"
          :submitting="submitting"
          @submit="handleSubmit"
          @play-again="playAgain"
          @change-tournament="changeTournament"
        />

        <div v-if="store.leaderboard.length" class="lb-section">
          <SlamLeaderboard :entries="store.leaderboard" />
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.slam-view { max-width: 800px; margin: 0 auto; padding: var(--space-6) var(--space-4); }
.slam-header { text-align: center; margin-bottom: var(--space-8); }
.slam-title { font-size: var(--font-size-3xl); font-weight: var(--font-weight-bold); margin-bottom: var(--space-2); }
.slam-desc { color: var(--color-text-muted); margin-bottom: var(--space-4); }

.steps { display: flex; align-items: center; justify-content: center; gap: var(--space-2); }
.steps span { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.steps span.active { color: var(--color-accent); font-weight: var(--font-weight-semibold); }
.steps span.done { color: var(--color-text-secondary); }
.step-sep { color: var(--color-border); }

.simulation-wrap { display: flex; flex-direction: column; align-items: center; gap: var(--space-4); }
.sim-progress { font-size: var(--font-size-sm); color: var(--color-text-muted); }

.result-wrap { display: flex; flex-direction: column; gap: var(--space-8); }
.lb-section { padding-top: var(--space-6); border-top: 1px solid var(--color-border); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/SlamView.vue
git commit -m "feat: add SlamView orchestrating all 4 game steps"
```

---

## Task 9: Router + navigation

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Add the `/slam` route**

Open `frontend/src/router/index.ts`. Add the lazy-loaded view alongside the other imports at the top:

```typescript
const SlamView = () => import('../views/SlamView.vue')
```

Add the route inside the `routes` array (after the Guides routes is a good place):

```typescript
{
    path: '/slam',
    name: 'Slam',
    component: SlamView,
    meta: {
        title: 'TE4 Slam',
        description: 'Build your champion from TE4 community players and simulate a Grand Slam tournament.'
    }
},
```

- [ ] **Step 2: Add nav link in App.vue**

Open `frontend/src/App.vue`. At the top of the `<script setup>` block, add `Trophy` to the lucide import:

```typescript
import { Activity, BarChart2, Globe, Shirt, Clapperboard, LogOut, Database, Shield, ChevronDown, User, Trophy } from 'lucide-vue-next'
```

Inside the `<nav class="nav-links">` block, add the Slam link after the Guides link (before the admin template block):

```html
<div class="nav-divider"></div>
<RouterLink to="/slam" class="nav-link" active-class="active">
  <div class="icon-wrapper icon-slam">
    <Trophy class="nav-icon" :size="20" stroke-width="2.5" />
  </div>
  <span>TE4 Slam</span>
</RouterLink>
```

Add a color variable for the new icon (find the existing `.icon-guides` style in App.vue and add after it):

```css
.icon-slam { color: var(--color-warning, #f59e0b); }
```

- [ ] **Step 3: Verify the route loads**

```bash
cd frontend
npm run dev
```

Navigate to `http://localhost:5173/slam`. Expected: TournamentPicker screen renders with 4 slam cards (empty data until backend is running, but no console errors).

- [ ] **Step 4: Run type check**

```bash
cd frontend
npm run type-check
```

Expected: no type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router/index.ts frontend/src/App.vue
git commit -m "feat: add /slam route and nav link for TE4 Slam game"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Task |
|-----------------|------|
| `slam_players` model with 9 skills | Task 1 |
| `slam_runs` model | Task 1 |
| Alembic migration | Task 1 |
| `GET /api/slam/players` | Task 2 |
| `GET /api/slam/tournaments` | Task 2 |
| `POST /api/slam/runs` | Task 2 |
| `GET /api/slam/leaderboard/{slug}` | Task 2 |
| `GET /api/slam/stats/{slug}` | Task 2 |
| `GET /api/slam/profile/{nickname}` | Task 2 |
| Admin CRUD for players | Task 2 |
| OVR formula (weighted + weak link + surface) | Task 3 |
| `setWinProb` + `matchWinProb` + `simulateMatch` | Task 3 |
| `drawOpponents` (random, sorted by OVR) | Task 3 |
| `simulateTournament` | Task 3 |
| Pinia store with draft logic | Task 4 |
| Draft mode (one player per skill) | Task 6 |
| Tournament picker (4 slams) | Task 5 |
| Round-by-round simulation reveal | Task 7 + 8 |
| Result screen + stats | Task 7 |
| Leaderboard | Task 7 |
| `/slam` route | Task 9 |
| Nav link | Task 9 |

### Type consistency check
- `SkillKey` defined in `slamEngine.ts`, imported everywhere needed ✓
- `SlamPlayerData` used in store and engine ✓
- `DrawRound` defined in `slamEngine.ts`, used in store + `RunResult` + `SlamView` ✓
- `return_skill` used consistently as Python attr name; DB column aliased to `return` ✓
- `Tournament` type defined in `slam.ts` store ✓
