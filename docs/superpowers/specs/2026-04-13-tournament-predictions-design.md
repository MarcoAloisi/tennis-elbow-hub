# Tournament Predictions — Design Spec

**Date:** 2026-04-13  
**Feature:** XKT Tour — Tournament Predictions section  
**Status:** Approved

---

## Overview

A tournament prediction game embedded in the XKT Online Tour tab. An admin selects a managames.com tournament, users anonymously predict the full bracket (with optional score predictions), and a live leaderboard tracks standings as match results come in. When the admin closes the tournament, a top-3 podium is revealed. All past tournaments are archived.

---

## Route

New dedicated sub-route: `/online-tours/xkt/predictions`

Linked from the XKT tab via a "Tournament Predictions →" card (same pattern as the WTSL tab's "Tour Statistics" card). A new `PredictionView.vue` handles this route.

The existing router children for `/online-tours/xkt` gain an additional nested route:
```
/online-tours/xkt/predictions          — tournament list + active tournament
/online-tours/xkt/predictions/:slug    — specific past tournament (read-only)
```

---

## Architecture

### Backend — 2 new SQLAlchemy models

**`PredictionTournament`**
```
id                  int, PK
name                str        e.g. "Monte-Carlo 2026 (Singles)"
managames_url       str        full OT_ViewTournament.php URL
trn_id              int        the ?Trn= parameter
slug                str        unique, URL-safe, auto-generated from name
draw_data           JSON       parsed bracket structure (see below)
status              str        "open" | "closed" | "finished"
predictions_close_at datetime  admin-set deadline
created_at          datetime
updated_at          datetime
```

**`PredictionEntry`**
```
id                  int, PK
tournament_id       int, FK → PredictionTournament.id
nickname            str        max 30 chars, trimmed
ip_address          str        stored at submission time
picks               JSON       {match_id: {winner: str, score?: str}}
total_score         int        recomputed on each admin refresh (default 0)
submitted_at        datetime
```

Unique constraints:
- `(tournament_id, ip_address)` — one submission per IP per tournament
- `(tournament_id, nickname)` — one submission per nickname per tournament

### `draw_data` JSON structure

```json
{
  "sections": ["qualifying", "main"],
  "rounds": {
    "qualifying": ["Q1", "Q2", "Qualified"],
    "main": ["R1", "R2", "R3", "QF", "SF", "F"]
  },
  "matches": [
    {
      "id": "main_R1_1",
      "section": "main",
      "round": "R1",
      "player1": {"name": "Jira", "seed": 1, "player_id": "48100"},
      "player2": {"name": "MagRai", "seed": null, "player_id": "60880"},
      "winner": "Jira",
      "score": "6/0 6/0"
    }
  ]
}
```

`winner` and `score` are `null` until the match is played. They are populated by admin-triggered re-scrapes.

---

## Backend Endpoints

All prediction endpoints live under `/api/predictions`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/predictions/tournaments` | Public | List all tournaments (active + past) |
| GET | `/api/predictions/tournaments/:slug` | Public | Get tournament detail + draw_data |
| POST | `/api/predictions/tournaments` | Admin | Create tournament (scrape draw from URL) |
| POST | `/api/predictions/tournaments/:id/refresh` | Admin | Re-scrape managames + recompute scores |
| POST | `/api/predictions/tournaments/:id/close` | Admin | Set status = "closed" (predictions locked) |
| POST | `/api/predictions/tournaments/:id/finish` | Admin | Set status = "finished" (podium revealed) |
| DELETE | `/api/predictions/tournaments/:id` | Admin | Delete tournament + all entries |
| GET | `/api/predictions/tournaments/:id/entries` | Public | All entries + scores (nickname, score, picks) |
| POST | `/api/predictions/tournaments/:id/entries` | Public | Submit a prediction |
| DELETE | `/api/predictions/entries/:id` | Admin | Remove a suspicious/duplicate entry |

---

## Submission Anti-Abuse

Three layered controls:

1. **IP lock** (primary) — `(tournament_id, ip_address)` unique constraint in DB. Returns 409 if same IP submits twice.
2. **Nickname lock** (secondary) — `(tournament_id, nickname)` unique constraint. Returns 409 if nickname taken.
3. **localStorage token** (tertiary) — frontend stores a `prediction_submitted_{tournament_id}` key in localStorage on successful submit, disabling the form UI in the same browser session.
4. **Admin deletion** — admin can remove any entry from the management panel.

---

## Scoring System

Points are awarded per correctly predicted match. Wrong winner = 0 pts for that match regardless of score.

### Base points by round (correct winner required)

Qualifying rounds (Q1, Q2) are displayed in the bracket for completeness but are **not scored** — only main draw rounds count toward points.

| Round | Winner only | Correct sets count | Exact score (all sets) |
|-------|-------------|-------------------|----------------------|
| R1    | 5           | 15                | 30                   |
| R2    | 10          | 25                | 50                   |
| R3    | 15          | 35                | 70                   |
| QF    | 20          | 50                | 100                  |
| SF    | 30          | 75                | 150                  |
| F     | 50          | 100               | 200                  |

### Score bonus breakdown

Given a correct winner pick with an optional score prediction:

- **No score provided / score unparseable** → winner-only base points
- **Score provided:**
  - **Correct sets count**: predicted 2 sets (e.g. `6/3 6/2`) and the match was won in 2 sets, OR predicted 3 sets (e.g. `6/3 3/6 7/5`) and it went to 3 sets → use "correct sets count" column
  - Each individual set score exactly right: **+3 pts** per set
  - All set scores exactly right: full "exact score" column value (replaces per-set bonus)

**Example — SF: user predicts Jira def. gifu 6/3 3/6 6/1, actual: Jira def. gifu 6/3 3/6 7/5**
- Correct winner ✓ → qualifies
- 3 sets correct ✓ → base 75 pts
- Set 1 `6/3` correct → +3 pts
- Set 2 `3/6` correct → +3 pts
- Set 3 wrong → 0
- Not exact → no exact bonus
- **Total: 81 pts**

Score parsing: stored as free text (e.g. `"6/3 3/6 7/5"`), normalised to `["6/3", "3/6", "7/5"]` at compute time. Parser strips whitespace and handles both `/` and `-` separators.

### Score recomputation

Triggered only by admin "Refresh Results". The backend:
1. Re-scrapes `OT_ViewTournament.php` for the tournament
2. Updates `draw_data` with real match results
3. Iterates all `PredictionEntry` rows for this tournament
4. Recomputes `total_score` for each entry by comparing `picks` against `draw_data.matches[*].winner` and `.score`
5. Commits all updated scores in a single transaction

---

## Frontend Structure

### `PredictionView.vue`
Top-level view at `/online-tours/xkt/predictions`.

**If no active tournament:** shows archive list only.  
**If active tournament:** shows tournament banner + tabs, then archive below.

### Tournament banner
Shows name, surface, category, draw size, deadline countdown, status badge (`OPEN` / `CLOSED` / `FINISHED`).

### Three tabs (inside an active/past tournament)

**1. My Prediction**
- Before deadline + no submission: interactive bracket editor
  - Left-to-right rounds (R1 → F), each match cell has two clickable players
  - Clicking a player marks them selected, the other struck through, and propagates their name as TBD into the next round
  - Unpicked next-round slots show "TBD" (not pre-filled with seeds)
  - After picking a winner, optional score input appears below the match cell
  - Score format hint shown: `e.g. 6/3 6/2` or `6/3 3/6 7/5`
  - Points available shown per match cell: `exact = +30 pts`
  - Nickname input + Submit button at the bottom
  - localStorage check disables editor if already submitted in this browser
- After deadline or already submitted: read-only view of own bracket with actual results overlaid (correct picks highlighted green, wrong picks struck through red)

**2. Leaderboard**
- Ranked table: position, nickname, correct matches count, progress bar, total score
- Top-1 highlighted in amber, current user's row (matched by localStorage nickname) highlighted in lime accent
- Live badge with pulsing dot while tournament is in progress
- After finish: podium (2nd–1st–3rd layout) above the full table

**3. All Predictions**
- Table: nickname, submitted_at, total_score
- Click any row to view that user's bracket in read-only mode (modal or expanded panel)

### Admin controls (visible only to `isAdmin` users)

A collapsible admin panel at the top of `PredictionView.vue`:
- **Add Tournament**: URL input + datetime picker for deadline + Publish button
- **Refresh Results**: re-scrapes managames and recomputes scores
- **Close Predictions**: locks submission (status → closed)
- **Mark Finished**: reveals podium (status → finished)
- **Delete Entry**: available inline in the All Predictions tab per row

### Historical archive

Below the active tournament, a grid of past tournament cards:
- Tournament name, surface, category, date
- Mini podium showing top-3 nicknames + scores
- "View Results →" link to `/online-tours/xkt/predictions/:slug` (read-only)

---

## Pinia Store

New `usePredictionsStore` store:

```ts
// State
tournaments: PredictionTournament[]
activeTournament: PredictionTournament | null
entries: PredictionEntry[]
myPicks: Record<string, { winner: string; score?: string }>  // keyed by match_id
myNickname: string
submittedTournamentIds: Set<number>  // from localStorage

// Actions
fetchTournaments()
fetchEntries(tournamentId)
submitPrediction(tournamentId, nickname, picks)
// Admin
createTournament(url, closeAt)
refreshResults(tournamentId)
closePredictions(tournamentId)
markFinished(tournamentId)
deleteEntry(entryId)
```

---

## Managames Scraper Extension

The existing `scraper.py` gets a new method `scrape_tournament_draw(url: str) -> dict` that:
1. Fetches the `OT_ViewTournament.php` page with `httpx` (same pattern as existing scraper)
2. Parses with BeautifulSoup
3. Extracts tournament metadata (name, surface, category, draw size, week, year)
4. Extracts the main draw table structure: each `<tr>` maps to a match slot, `rowspan` attributes determine round grouping
5. Extracts the qualifications table using the same logic
6. Returns the `draw_data` dict described above
7. On re-scrape, winner and score fields are populated from completed match cells

---

## Design Decisions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| Anonymous predictions | Lower friction, wider participation, matches community feel |
| IP lock over auth | No signup required; IP is a proportionate deterrent for a community game |
| One-shot submission | Prevents gaming predictions after seeing early results |
| Admin-triggered refresh | Avoids continuous scraping load; admin controls the cadence |
| Score stored as free text | Matches managames format exactly, easier to display |
| Qualifying bracket included | Keeps parity with the actual managames draw |

---

## Out of Scope

- Email notifications
- Points leaderboard across multiple tournaments (season standings)
- Tiebreaker rules (current tiebreaker: earlier submission wins)
- Mobile-optimised bracket (horizontal scroll is acceptable for v1)
