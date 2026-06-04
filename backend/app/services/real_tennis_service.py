"""Real tennis scores service — fetches from SofaScore, caches in memory."""

import asyncio
import time
from datetime import date, datetime, timezone
from typing import Any

import httpx

_SOFASCORE_BASE = "https://api.sofascore.com/api/v1"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
}
_CACHE_TTL = 30  # seconds
_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}


def _transform_event(event: dict) -> dict:
    """Map a raw SofaScore event dict to our internal RealMatch shape."""
    tournament_raw = event.get("tournament") or {}
    category_raw = tournament_raw.get("category") or {}
    round_raw = event.get("roundInfo") or {}
    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}
    status_raw = event.get("status") or {}
    status_type = status_raw.get("type", "")

    period_keys = ["period1", "period2", "period3", "period4", "period5"]
    sets: list[list[int]] = []
    for key in period_keys:
        p1 = home_score.get(key)
        p2 = away_score.get(key)
        if p1 is not None and p2 is not None:
            sets.append([p1, p2])

    if status_type == "inprogress":
        status = "live"
    elif status_type in ("finished", "ended", "afterpens", "awardedwin"):
        status = "completed"
    else:
        status = "upcoming"

    return {
        "id": event.get("id"),
        "player1": (event.get("homeTeam") or {}).get("name", "Unknown"),
        "player2": (event.get("awayTeam") or {}).get("name", "Unknown"),
        "score": {
            "sets": sets,
            "current_game": None,
        },
        "status": status,
        "start_timestamp": event.get("startTimestamp"),
        "tournament": {
            "id": tournament_raw.get("id"),
            "name": tournament_raw.get("name", ""),
            "category": category_raw.get("name", ""),
            "round": round_raw.get("name", ""),
        },
    }


def _extract_tournaments(matches: list[dict]) -> list[dict]:
    """Derive sorted tournament list from a flat list of RealMatch dicts."""
    seen: dict[Any, dict] = {}
    for match in matches:
        t = match["tournament"]
        tid = t["id"]
        if tid not in seen:
            seen[tid] = {**t, "match_count": 0}
        seen[tid]["match_count"] += 1
    return sorted(seen.values(), key=lambda x: x["match_count"], reverse=True)


async def fetch_real_tennis_scores() -> dict:
    """Return cached or freshly fetched real tennis scores from SofaScore."""
    now = time.time()

    if _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL:
        return {**_cache["data"], "stale": False}

    today = date.today().isoformat()
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS, timeout=10.0, follow_redirects=True
        ) as client:
            live_resp, today_resp = await asyncio.gather(
                client.get(f"{_SOFASCORE_BASE}/sport/tennis/events/live"),
                client.get(f"{_SOFASCORE_BASE}/sport/tennis/scheduled-events/{today}"),
            )
            live_resp.raise_for_status()
            today_resp.raise_for_status()
            live_events: list[dict] = live_resp.json().get("events") or []
            today_events: list[dict] = today_resp.json().get("events") or []
    except Exception:
        if _cache["data"] is not None:
            return {**_cache["data"], "stale": True}
        return {
            "live": [],
            "upcoming": [],
            "completed": [],
            "tournaments": [],
            "cached_at": None,
            "stale": True,
        }

    live_ids = {e["id"] for e in live_events}
    live_matches = [_transform_event(e) for e in live_events]

    upcoming: list[dict] = []
    completed: list[dict] = []
    for e in today_events:
        if e.get("id") in live_ids:
            continue
        m = _transform_event(e)
        if m["status"] == "upcoming":
            upcoming.append(m)
        elif m["status"] == "completed":
            completed.append(m)

    all_matches = live_matches + upcoming + completed
    data: dict = {
        "live": live_matches,
        "upcoming": upcoming,
        "completed": completed,
        "tournaments": _extract_tournaments(all_matches),
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache["data"] = data
    _cache["fetched_at"] = now
    return {**data, "stale": False}
