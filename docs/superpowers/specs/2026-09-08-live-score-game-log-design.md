# Live score game-by-game detail (design)

## Problem

Live score cards show only the current snapshot (current game points, set scores). The user wants a flashscore-style detail view: click a card, see how the match unfolded game by game (who served, final point score of each game, set by set), and have that history persisted forever, for both live and finished matches.

## Source constraint (drives the whole design)

The TE4 master server only returns a current-state snapshot per poll (`"6/3 4/6 -- 40:30•"`), re-parsed fresh every tick by `parse_live_state` (`backend/app/services/score_parser.py`). There is no event log or point-level history in the source — each poll is a full state, not a delta. Default poll interval is 60s (min 5s via `score_refresh_interval`), which is not fast enough to reliably catch every individual point (average ~15-20s/point) without a large increase in polling frequency and load on the master server.

**Decision: game-by-game granularity, not point-by-point.** Games change slowly enough (many points each) that diffing consecutive polls reliably catches every game transition at the current poll interval, with zero risk of missing a game. True point-by-point would require dropping the interval to ~2s and would still occasionally miss a point — rejected as not worth the reliability and load tradeoff.

## Scope

- Singles matches only (same universe as `StatsService`/`FinishedMatch`: real player names, both Elo present).
- Persisted permanently — game log rows are written incrementally as each game completes, independent of whether the match later qualifies for a `FinishedMatch` row (so even an abandoned/short match keeps whatever game history it accrued).
- Detail view works for both in-progress and finished matches, keyed by the same `match_id` used today (stable hash of `creation_time_ms:match_name:port`, see `GameServer.match_id`).

## Data model

New table `match_game_events`, new Alembic migration.

```python
class MatchGameEvent(Base):
    __tablename__ = "match_game_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String, index=True)
    set_number: Mapped[int] = mapped_column(Integer)
    game_number: Mapped[int] = mapped_column(Integer)  # p1_games + p2_games after this game
    p1_games: Mapped[int] = mapped_column(Integer)
    p2_games: Mapped[int] = mapped_column(Integer)
    winner: Mapped[int] = mapped_column(Integer)  # 1 or 2
    server: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 or 2, who served this game
    final_point_score: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "40-30", "7-5" if tiebreak
    is_tiebreak: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("match_id", "set_number", "game_number", name="uq_match_game_event"),
    )
```

The unique constraint makes writes idempotent — if a tick's diff logic ever double-fires for the same game (e.g. after a transient fetch failure and cache replay), the insert is a no-op via `ON CONFLICT DO NOTHING` (Postgres) / `INSERT OR IGNORE` (SQLite).

Rows are independent of `FinishedMatch` — no foreign key, joined only by `match_id` string at query time. This keeps the write path simple (no need to know at game-completion time whether the match will later qualify as finished).

## Backend: tick-diff service

New `backend/app/services/game_log_service.py`, mirroring the existing `_previous_matches` pattern in `stats_service.py`:

- In-memory `dict[str, LiveMatchState]` of last-seen state per `match_id`.
- Called once per poll tick from `ScraperService.fetch_servers`, alongside the existing `stats_service.track_matches` call, for the same `singles_servers` list already computed there (reuse, don't refilter).
- Per match, per tick:
  - No previous state recorded → store current state, no event (first sighting, nothing to diff against).
  - `current_set_games` sum increased, same `set_number` → a game just completed. Winner is whichever side's game count went up. `server`/`final_point_score`/`is_tiebreak` come from the **previous** tick's state (the last point score seen before the game closed, and whether that game was a tiebreak). Insert row.
  - `sets_won` total increased → the last game of the previous set completed (covers the tiebreak-decided-set case, where `current_set_games` may jump e.g. 6/6 → next set 0/0 rather than incrementing within the same set). Same insert logic, using the previous tick's `set_number` (derived from `len(sets_won_before)`, i.e. count of sets already recorded) and the previous tick's final game state.
  - Match disappears from the server list → nothing to do here; `stats_service.track_matches` already handles `FinishedMatch` write and its own cleanup. This service independently drops the match_id from its in-memory dict on the same "missing" detection (duplicate the missing-id computation already done in `track_matches`, or expose it — implementation detail for the plan).
- DB writes are `INSERT ... ON CONFLICT DO NOTHING`, fire-and-forget per game (not batched), swallow/log errors per match so one match's failure never blocks others in the tick (same `return_exceptions=True` pattern used for win-probability in `scraper.py`).

## API

`GET /api/scores/{match_id}/games` in `live_scores.py`:

- `@limiter.limit("60/minute")`, public, no auth.
- Metadata: if the match is still in the live cache (`scraper.get_latest_data()`), pull players/elo/surface/mod/current score from there; otherwise fall back to the `FinishedMatch` row by `match_id`. If neither exists, 404.
- Body: metadata block + `games: list[...]` ordered by `(set_number, game_number)`, queried from `match_game_events` by `match_id`.
- No pagination — a full match tops out around 20-30 rows.

## Frontend

- New modal component (e.g. `MatchDetailModal.vue`), opened on score-card click from the live scores view.
- Fetches `apiUrl('/api/scores/{match_id}/games')` on open.
- Renders grouped by set: each set header (final set score) followed by its games in order — "Juego 3: 40-30, sacó Player1, ganó Player1" style rows, tiebreaks flagged distinctly.
- If the match is still live (metadata says in-progress), the modal polls the same endpoint on an interval (reuse an existing polling composable pattern) to append new games as they complete; no new WebSocket channel.
- Modal closes back to the same scroll position in the live scores list (no route change, per the modal-not-page decision).

## Error handling

- Missing/incomplete snapshot diffs (e.g. a game count that jumps by more than 1 between polls, which can happen after a transient fetch failure that skipped a tick) are recorded as a single game event using the last known state — no attempt to fabricate the missing intermediate game. This is a known gap inherent to snapshot polling, not something to solve here.
- `match_game_events` writes never block or fail the score broadcast — same isolation pattern as the existing win-probability computation in `scraper.py`.

## Testing

- Parser/diff unit tests: feed `game_log_service` a sequence of synthetic `LiveMatchState` snapshots (game win, set win via tiebreak, set win by 2-game margin, match end) and assert the exact rows it would write.
- API test: seed `match_game_events` + a `FinishedMatch`, assert `GET /api/scores/{match_id}/games` shape.
- Frontend: component test for the modal rendering a fixed games payload, grouped by set.
