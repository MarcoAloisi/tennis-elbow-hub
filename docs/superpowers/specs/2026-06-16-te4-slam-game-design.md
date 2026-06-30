# TE4 Slam — Game Design Spec

**Date:** 2026-06-16
**Feature:** A "build your champion" simulation game for the TE4 online community, inspired by theslam.app. Users draft skills from real community players to create a Frankenstein composite player, then simulate a Grand Slam tournament.

---

## Overview

Users visit a new `/slam` page, choose one of the 4 Grand Slams, draft 9 skills from different community players (one player per skill — draft mode), and simulate the full tournament bracket. Opponents are drawn randomly each run. Results are saved to the backend for global stats and a leaderboard. Users can play as many times as they want.

---

## Tournament Config (hardcoded, no DB table)

```python
TOURNAMENTS = {
    "ao":        {"name": "Australian Open", "surface": "hard",  "best_of": 5, "rounds": 7},
    "rg":        {"name": "Roland Garros",   "surface": "clay",  "best_of": 5, "rounds": 7},
    "wimbledon": {"name": "Wimbledon",        "surface": "grass", "best_of": 5, "rounds": 7},
    "uso":       {"name": "US Open",          "surface": "hard",  "best_of": 5, "rounds": 7},
}
# Future Masters 1000: best_of=3, rounds=6
```

---

## Data Models

### `slam_players` — community players with skill values (admin-managed)

| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | |
| name | VARCHAR(50) | Display name (e.g. "Jira") |
| slug | VARCHAR(60) | URL-safe unique key |
| avatar_color | VARCHAR(7) | Hex color for avatar chip |
| serve | INT 0-100 | |
| return | INT 0-100 | |
| slice | INT 0-100 | |
| forehand | INT 0-100 | |
| backhand | INT 0-100 | |
| short_accels | INT 0-100 | |
| pure_defense | INT 0-100 | |
| net_game | INT 0-100 | |
| trickshots | INT 0-100 | |

### `slam_runs` — every simulation run (all stored, no restrictions)

| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | |
| tournament_slug | VARCHAR(20) | ao / rg / wimbledon / uso |
| nickname | VARCHAR(30) | User-chosen display name |
| build | JSON | `{serve:"Jira", return:"MagRai", ...}` — one player per skill |
| draw | JSON | `[{round:1, opponent:"Jira", opp_ovr:82, won:true, score:"3-1"}, ...]` |
| ovr | INT | Composite player's final OVR |
| round_reached | INT | 1-7 (7 = champion) |
| champion | BOOL | True if won all rounds |
| played_at | TIMESTAMP | |

Index on `(tournament_slug, champion)` for leaderboard queries.
Index on `(nickname)` for profile queries.

---

## Simulation Logic (runs entirely in the frontend — TypeScript)

### Step 1 — OVR calculation

Weighted average + weakest link penalty. Weights vary by surface.

```typescript
const WEIGHTS_BASE = {
  serve: 1.4, return: 1.3, forehand: 1.3, backhand: 1.1,
  short_accels: 1.2, pure_defense: 1.0, net_game: 0.7,
  trickshots: 0.7, slice: 1.0,
}

const SURFACE_OVERRIDES: Record<string, Partial<typeof WEIGHTS_BASE>> = {
  grass: { serve: 1.7, net_game: 1.0, return: 1.1 },
  clay:  { short_accels: 1.6, pure_defense: 1.4, serve: 0.9 },
  hard:  {},
}

function getWeights(surface: string) {
  return { ...WEIGHTS_BASE, ...(SURFACE_OVERRIDES[surface] ?? {}) }
}

function calcOVR(skills: Record<string, number>, surface: string, lambda = 0.2): number {
  const weights = getWeights(surface)
  const keys = Object.keys(skills)
  const sumW = keys.reduce((s, k) => s + weights[k], 0)
  const weighted = keys.reduce((s, k) => s + weights[k] * skills[k], 0) / sumW
  const worst = Math.min(...keys.map(k => skills[k]))
  return Math.round((1 - lambda) * weighted + lambda * worst)
}
```

### Step 2 — Match simulation

```typescript
function setWinProb(myOVR: number, oppOVR: number, scale = 40): number {
  return 1 / (1 + Math.pow(10, (oppOVR - myOVR) / scale))
}

function matchWinProb(p: number, bestOf: number): number {
  const q = 1 - p
  if (bestOf === 5) return p**3 * (1 + 3*q + 6*q**2)
  if (bestOf === 3) return p**2 * (1 + 2*q)
  return p
}

function simulateMatch(myOVR: number, oppOVR: number, bestOf: number): { won: boolean; score: string } {
  const p = setWinProb(myOVR, oppOVR)
  const needed = Math.ceil(bestOf / 2)
  let me = 0, opp = 0
  while (me < needed && opp < needed) {
    Math.random() < p ? me++ : opp++
  }
  return { won: me === needed, score: `${me}-${opp}` }
}
```

### Step 3 — Tournament simulation

Opponents are a random sample from `slam_players`, sorted ascending by OVR (easier opponents first, hardest in final).

```typescript
function simulateTournament(myOVR: number, opponents: SlamPlayer[], tournament: Tournament) {
  const draw = []
  for (let r = 0; r < opponents.length; r++) {
    const opp = opponents[r]
    const result = simulateMatch(myOVR, opp.ovr, tournament.best_of)
    draw.push({ round: r + 1, opponent: opp.name, opp_ovr: opp.ovr, ...result })
    if (!result.won) break
  }
  return draw
}
```

---

## API Endpoints

All under prefix `/api/slam`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/players` | All slam players with their 9 skill values |
| GET | `/tournaments` | Tournament config list |
| POST | `/runs` | Save a completed run |
| GET | `/leaderboard/{tournament_slug}` | Top runs: most wins by nickname + highest OVR runs |
| GET | `/stats/{tournament_slug}` | Global stats: % champions today, total runs today, all-time champ count |
| GET | `/profile/{nickname}` | All runs for a nickname (history + builds) |
| GET | `/players/{id}` | Single player (admin) |
| POST | `/players` | Create player (admin) |
| PUT | `/players/{id}` | Update player skills (admin) |
| DELETE | `/players/{id}` | Delete player (admin) |

Rate limits: public endpoints 60/min, POST /runs 30/min.

---

## UI Flow — 4 Steps

### Step 1: Choose Tournament
4 cards for AO / RG / Wimbledon / USO. Each shows surface, best-of format, and which skills are boosted on that surface.

### Step 2: Draft Build (draft mode)
9 skill slots displayed in order: serve → return → slice → forehand → backhand → short_accels → pure_defense → net_game → trickshots.

For each slot, a picker shows all `slam_players`. Players already drafted are visually disabled and unselectable. Picking a player for a slot locks them from all other slots. User can go back to a previous slot to change their pick (releases that player back to the pool).

OVR updates live as skills are filled. Build is complete when all 9 are filled.

### Step 3: Simulate
Round-by-round reveal. For each round:
- Show opponent name + OVR
- Animate the match (show set scores as they're "played")
- Show won/lost with score (e.g. "3-1")
- If lost → eliminated, go to step 4

### Step 4: Results
- Champion screen or "Eliminated in Round X" screen
- Global stats: "X% of players won today on this slam"
- Leaderboard snippet: top champions by wins
- "Play again" button → back to step 2 (same tournament, new draft)
- "Change tournament" → back to step 1

---

## Frontend Location

- Route: `/slam`
- New view: `frontend/src/views/SlamView.vue`
- New store: `frontend/src/stores/slam.ts`
- New components under `frontend/src/components/slam/`:
  - `TournamentPicker.vue`
  - `SkillDraft.vue`
  - `SimulationRound.vue`
  - `RunResult.vue`
  - `SlamLeaderboard.vue`

---

## Admin

Extend existing admin panel or add a `/admin/slam` sub-section to manage `slam_players`: create, edit skill values, delete. No special tooling needed — a simple table with editable rows.

---

## Not in scope (v1)

- Masters 1000 tournaments (architecture supports it, add when ready)
- User accounts / auth (nickname-based, anonymous)
- Social sharing cards
- Streaks (can be derived from `slam_runs` by nickname later)
