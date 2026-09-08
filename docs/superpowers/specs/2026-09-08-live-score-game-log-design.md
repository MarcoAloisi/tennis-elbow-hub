# Live score game-by-game detail (design)

## Problem

Live score cards show only the current snapshot (current game points, set scores). The user wants a flashscore-style detail view: click a card, see how the match unfolded game by game (who served, final point score of each game, set by set), and have that history persisted forever, for both live and finished matches.

## Source constraint (drives the whole design)

The TE4 master server only returns a current-state snapshot per poll (`"6/3 4/6 -- 40:30•"`), re-parsed fresh every tick by `parse_live_state` (`backend/app/services/score_parser.py`). There is no event log or point-level history in the source — each poll is a full state, not a delta. Poll interval defaults to 5s (`Settings.score_refresh_interval` in `config.py`; the `60` fallback in `main.py`'s `getattr(settings, "score_refresh_interval", 60)` is dead code — the field always exists), floored at 5s. That's still not fast enough to reliably catch every individual point (average ~15-20s/point — two points can close between polls) without dropping well under 5s and raising load on the master server further.

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

The unique constraint makes writes idempotent — if a tick's diff logic ever double-fires for the same game (e.g. after a transient fetch failure and cache replay), the duplicate insert raises `IntegrityError` and is dropped. Written the same way `_try_finish_match` already does it in `stats_service.py` (`session.add()` + `flush()` inside `try/except IntegrityError: rollback`) — no dialect-specific `ON CONFLICT`/`INSERT OR IGNORE` SQL, which would need a Postgres and a SQLite branch to keep working on both backends. One idiom for "insert, ignore if it already exists" in this codebase, not two.

Rows are independent of `FinishedMatch` — no foreign key, joined only by `match_id` string at query time. This keeps the write path simple (no need to know at game-completion time whether the match will later qualify as finished).

## Backend: tick-diff service

New `backend/app/services/game_log_service.py`. State-tracking shape follows `stats_service._previous_matches`, but the two caches are **not shared** — `stats_service` needs full `GameServer` objects for rename detection and match-finish bookkeeping; this service only ever needs the parsed `LiveMatchState` (games/sets/server/points), a strictly smaller and simpler need. Sharing a cache between them would couple two independent concerns for no benefit; keeping them separate is the simpler code, not the duplicated code.

**Avoiding a duplicate parse:** `GameServer.live_state` is a Pydantic `@computed_field` — it re-runs `parse_live_state` on every access, it isn't cached. `scraper.fetch_servers` already calls `server.live_state` once per singles server inside `_apply_win_probability`. Rather than have `game_log_service` call `.live_state` again on the same `GameServer` object in the same tick (parsing the same score string twice), `fetch_servers` computes it once per singles server into a local `dict[str, LiveMatchState]` and passes that to both `_apply_win_probability` and `game_log_service.record_tick` — one parse per server per tick, not two.

`record_tick(current_states: dict[str, LiveMatchState]) -> None`, called once per poll tick from `ScraperService.fetch_servers` right after that dict is built:

```python
for match_id, current in current_states.items():
    previous = self._previous.get(match_id)
    if previous is not None:
        await self._maybe_record_game(match_id, previous, current)
    self._previous[match_id] = current

# Drop state for matches no longer present this tick — this service only
# needs to stop tracking them, not run stats_service's rename/finish
# detection, so a plain key-set difference against this tick's own dict
# is enough; no need to depend on stats_service's bookkeeping.
for stale_id in self._previous.keys() - current_states.keys():
    del self._previous[stale_id]
```

`_maybe_record_game(match_id, previous, current)` — the exact, unambiguous diff (no hand-wavy "sum increased" check):

```python
prev_sets_total = sum(previous.sets_won)
curr_sets_total = sum(current.sets_won)

if curr_sets_total > prev_sets_total:
    # The game in progress last tick closed out the set (straight games or tiebreak).
    set_number = prev_sets_total + 1
    winner = 1 if current.sets_won[0] > previous.sets_won[0] else 2
elif sum(current.current_set_games) > sum(previous.current_set_games) and curr_sets_total == prev_sets_total:
    # A game closed mid-set.
    set_number = curr_sets_total + 1
    winner = 1 if current.current_set_games[0] > previous.current_set_games[0] else 2
else:
    return  # no game completed this tick

# `previous.current_set_games` is always the pre-game count in both branches
# above (branch 1 never bumped it — that snapshot's set was still "in
# progress" — and branch 2 diffs against it directly), so the +1 is applied
# exactly once here, not per-branch.
p1, p2 = previous.current_set_games
if winner == 1:
    p1 += 1
else:
    p2 += 1

await self._insert_event(
    match_id, set_number, game_number=p1 + p2, p1_games=p1, p2_games=p2,
    winner=winner, server=previous.server,
    final_point_score=f"{previous.current_points[0]}-{previous.current_points[1]}" if previous.current_points else None,
    is_tiebreak=previous.is_tiebreak,
)
```

`server`/`final_point_score`/`is_tiebreak` always come from `previous` — that's the last point state seen before the game closed. `_insert_event` writes and swallows/logs its own errors per match, called via `asyncio.gather(..., return_exceptions=True)` across matches in the same tick — same isolation pattern already used for win-probability in `scraper.py`, so one match's write failure never blocks another's.

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
- Frontend: no component-test framework exists yet in this repo (`vitest` is a bare script with no config, no `@vue/test-utils`, zero test files anywhere under `frontend/src`) — standing one up is out of scope for this feature. Verified manually instead: run the dev server, click a live card, confirm the modal shows the right games grouped by set for both a live and a finished match.
