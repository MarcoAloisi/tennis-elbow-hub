# Live score game-by-game detail (design)

Revised 2026-10-12: adds the best-effort point trail, drops the metadata half of the endpoint, wires the Results tab (saved scores), and trims the schema.

## Problem

Live score cards show only the current snapshot. The user wants a Sofascore-style detail view. Click a match, see how it unfolded game by game (who served, how each game went, set by set). History is persisted for live and finished matches.

## Source constraint (drives the design)

The TE4 master server returns only a current-state snapshot per poll (`"6/3 4/6 -- 40:30•"`), re-parsed every tick by `parse_live_state` (`backend/app/services/score_parser.py`). There is no event log. The poll interval defaults to 5s (`Settings.score_refresh_interval`), floored at 5s. A point takes roughly 15-20s (estimate from the first draft, not measured), so two points can close between polls.

**Decision: two layers of granularity.**
- **Game rows are exact.** A game changes slowly enough that diffing consecutive polls catches every game close.
- **Point trail is best effort.** Per game, store the distinct point scores that polling happened to observe, in order (`["0-0", "15-0", "30-15", "40-15"]`). Points between two polls can be missing. The winning point is never observed (the snapshot resets once the game closes), so the UI appends the winner as the last step.

True point-by-point stays rejected. It would need ~2s polling against the master server and would still be lossy.

## Scope

- Singles only, same universe as `StatsService`/`FinishedMatch`.
- Persisted permanently. Rows are written as each game completes, independent of whether the match later qualifies for a `FinishedMatch` row.
- Works for live and finished matches, keyed by `match_id` (stable hash of `creation_time_ms:match_name:port`, `GameServer.match_id`).
- Entry points are the live `MatchCard` and the Results tab `ResultCard`. Results older than this feature have no rows and show an empty state.

## Where the data lives

Prod Postgres is on the IONOS VPS (`localhost:5432/te4hub`). Supabase is Auth only (`DEPLOYMENT.md`). The new table goes through Alembic like every other table, and `infra/deploy.sh` runs `alembic upgrade head` on the VPS. Two rules follow.
- Generate the migration against the local Docker Postgres (`te4-pg`), not SQLite, so column types match prod.
- Never apply it through the Supabase MCP. That project is a stale copy and does not show prod.

## Data model

New table `match_game_events`, new Alembic migration. The natural key is the identity, so no surrogate `id`, no separate unique constraint and no extra index. The composite primary key already serves `WHERE match_id = ? ORDER BY set_number, game_number`.

```python
class MatchGameEvent(Base):
    __tablename__ = "match_game_events"

    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    set_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_number: Mapped[int] = mapped_column(Integer, primary_key=True)  # p1_games + p2_games after this game
    p1_games: Mapped[int] = mapped_column(Integer)
    p2_games: Mapped[int] = mapped_column(Integer)
    winner: Mapped[int] = mapped_column(Integer)  # 1 or 2
    server: Mapped[int | None] = mapped_column(Integer, nullable=True)  # who served this game
    is_tiebreak: Mapped[bool] = mapped_column(Boolean, default=False)
    points: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # observed point scores, best effort
```

Dropped from the first draft. `final_point_score` was really the last observed score, not the final one, and equals `points[-1]`. `created_at` had no reader. Both extra indexes were redundant with the primary key.

The Pydantic response schema `GameEventOut` (`from_attributes=True`, no `match_id`) lives in the same file, per the repo's co-location convention.

A duplicate insert raises `IntegrityError` and is dropped, the same idiom as `stats_service._try_finish_match` (`add` + `commit` in `try/except IntegrityError`). No dialect-specific SQL.

Rows are independent of `FinishedMatch`. No foreign key, joined only by the `match_id` string.

## Backend: tick-diff service

New `backend/app/services/game_log_service.py`. It keeps its own per-match cache, separate from `stats_service._previous_matches`. This service needs only the parsed `LiveMatchState` plus the observed point trail.

`GameServer.live_state` is a `@computed_field` that re-parses on every access. `fetch_servers` computes it once per singles server into a `dict[str, LiveMatchState]` and passes that to both `_apply_win_probability` and `record_tick`.

The logic is a small state machine with a pure, synchronous core.

```python
@dataclass
class _Tracked:
    state: LiveMatchState
    points: list[str]   # distinct point scores seen during the game in progress

def step(self, match_id, current) -> MatchGameEvent | None:
    tracked = self._tracked.get(match_id)
    trail = tracked.points if tracked else []
    event = diff_game(match_id, tracked.state, current, trail) if tracked else None
    if event:
        trail = []  # the closed game's trail is on the event; the new game starts empty
    snap = f"{current.current_points[0]}-{current.current_points[1]}" if current.current_points else None
    if snap and (not trail or trail[-1] != snap):
        trail.append(snap)
    self._tracked[match_id] = _Tracked(current, trail)
    return event
```

`diff_game(match_id, previous, current, points)` returns a `MatchGameEvent` (unpersisted ORM instance, no intermediate dataclass) or `None`.
- If `sum(current.sets_won) > sum(previous.sets_won)`, the game closed a set. `set_number = prev_sets_total + 1`, and the winner is whoever's `sets_won` rose.
- Else if the games in the current set rose and `sets_won` is unchanged, a game closed mid-set. `set_number = curr_sets_total + 1`, and the winner is whoever's games rose.
- Else return `None`.
- `p1, p2 = previous.current_set_games`, then the winner gets +1 exactly once. `game_number = p1 + p2`. `server` and `is_tiebreak` come from `previous`. `points` is the trail so far.

`record_tick(states)` calls `step` for every match, drops tracked state for matches absent from this tick, then persists the collected events one at a time. A failed insert is logged and never raised.

**Last game of a match.** A match is "finished" when it vanishes from the feed. Measured on the stale Sep-6 copy of `finished_matches`, 47,772 of 56,194 parseable scores (85%) end on a completed set. The last snapshot before a match vanishes therefore normally shows the clinching game, and the diff records it. The remainder are quits and short formats, where no clinching game exists.

## API

`GET /api/scores/{match_id}/games` in `live_scores.py`.
- Public, `@limiter.limit("60/minute")`, `response_model=list[GameEventOut]`.
- Returns the rows ordered by `(set_number, game_number)`. An unknown or pre-feature match returns `[]`, not 404.
- No metadata. The client already holds players, Elo, surface, mod and score on the live card or the Results row, so the endpoint does no live-cache lookup and no `FinishedMatch` fallback.
- No pagination (a match is at most a few dozen rows).

## Frontend

- One `MatchDetailModal.vue` mounted once in `LiveScoresView`. Props are `open`, a `MatchRef` (`matchId`, `player1`, `player2`, `isLive`) and an optional `refreshKey`.
- Entry points are a real `<button>` inside `MatchCard` (hidden for doubles) and inside `ResultCard`, forwarded through `ResultsTab`. A button instead of a clickable card keeps keyboard access and avoids nested interactive controls.
- The modal fetches `apiUrl('/api/scores/{id}/games')` on open and refetches when `refreshKey` changes. For a live match the view passes the live `score` string from the scores store. No timer, no extra WebSocket, and requests fire only when the match state moves. `record_tick` commits before the broadcast, so a changed score always has its row ready.
- A failed refetch keeps the games already shown. The error state appears only when nothing has loaded.
- Rendering groups games by set. Each row shows `Game N`, the game score, the server and the point trail (`0-0 → 15-0 → 30-15 → 40-15 → Game <winner>`), tiebreaks flagged. A caption says the point trail is best effort. The empty state reads "No game history recorded for this match."
- Reuse the global `.modal-overlay` from `components.css` and `useModalAccessibility`. Scoped CSS covers only the game list.

## Error handling

- A skipped tick can make a game count jump by more than one. That is recorded as one event from the last known state. No fabricated intermediate games.
- A backend restart loses the in-memory trail for the game in progress, so that one game has a partial trail. Known and accepted.
- `record_tick` is called inside `try/except` at the call site, so no failure can break the score broadcast. This is the same isolation as win probability. Like `track_matches` it awaits DB writes in the poll loop, an accepted precedent.

## Testing

- Pure tests, no DB. Feed `step`/`diff_game` snapshot sequences (game win both ways, set win by games, set win by tiebreak, no-change tick, trail dedupe and reset between games, first-sighting).
- Two DB tests against an in-memory SQLite session factory injected by monkeypatch (duplicate insert is a no-op, endpoint returns ordered rows with `points` round-tripped). No test writes to the dev database.
- No frontend test framework exists in the repo, so the UI is verified manually in the browser.
