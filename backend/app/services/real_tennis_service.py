"""Real tennis scores service — fetches from AllSports API, caches in memory."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings

_ALLSPORTS_BASE = "https://apiv2.allsportsapi.com/tennis/"
_HEADERS = {"Accept": "application/json"}

# 15-minute cache keeps us within AllSports free tier (100 req/day)
_CACHE_TTL = 900
_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_fetch_lock = asyncio.Lock()


def _categorize(league_name: str) -> tuple[str, str]:
    """Split 'ATP - Roland Garros' into ('ATP', 'Roland Garros')."""
    name = (league_name or "").strip()
    for prefix in ("ATP - ", "ATP – ", "WTA - ", "WTA – ", "ATP ", "WTA "):
        if name.upper().startswith(prefix.upper()):
            cat = prefix.strip().rstrip(" -–")
            return cat.upper(), name[len(prefix):].strip()
    if name.upper().startswith("ATP"):
        return "ATP", name[3:].lstrip(" -–").strip()
    if name.upper().startswith("WTA"):
        return "WTA", name[3:].lstrip(" -–").strip()
    return "", name


def _parse_sets(result_str: str) -> list[list[int]]:
    """Parse '6-4 7-5' into [[6, 4], [7, 5]]."""
    if not result_str or result_str in ("-", ""):
        return []
    sets = []
    for part in result_str.split():
        if "-" in part:
            try:
                a, b = part.split("-", 1)
                sets.append([int(a), int(b)])
            except ValueError:
                pass
    return sets


def _transform_event(event: dict) -> dict:
    """Map an AllSports tennis event to our internal RealMatch shape."""
    raw_status = str(event.get("event_status") or "").strip().lower()

    if raw_status == "notstarted":
        status = "upcoming"
    elif raw_status in ("finished", "ft", "after extra time", "aet", "ended"):
        status = "completed"
    else:
        status = "live"

    start_timestamp = None
    date_str = event.get("event_date", "")
    time_str = event.get("event_time", "")
    if date_str and time_str:
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            start_timestamp = int(dt.replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            pass

    category, t_name = _categorize(event.get("league_name", ""))

    return {
        "id": str(event.get("event_key", "")),
        "player1": event.get("event_home_team") or "Unknown",
        "player2": event.get("event_away_team") or "Unknown",
        "score": {
            "sets": _parse_sets(event.get("event_final_result", "")),
            "current_game": None,
        },
        "status": status,
        "start_timestamp": start_timestamp,
        "tournament": {
            "id": str(event.get("league_key", "")),
            "name": t_name,
            "category": category,
            "round": event.get("league_round", ""),
        },
    }


def _extract_tournaments(matches: list[dict]) -> list[dict]:
    """Derive sorted tournament list from match data."""
    seen: dict[str, dict] = {}
    for match in matches:
        t = match["tournament"]
        tid = t["id"]
        if not tid:
            continue
        if tid not in seen:
            seen[tid] = {**t, "match_count": 0}
        seen[tid]["match_count"] += 1
    return sorted(seen.values(), key=lambda x: x["match_count"], reverse=True)


async def fetch_real_tennis_scores() -> dict:
    """Return cached or freshly fetched real tennis scores from AllSports."""
    now = time.time()

    if _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL:
        return {**_cache["data"], "stale": False}

    async with _fetch_lock:
        now = time.time()
        if _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL:
            return {**_cache["data"], "stale": False}

        return await _do_fetch(now)


async def _do_fetch(now: float) -> dict:
    """Fetch live scores + today's fixtures from AllSports and merge."""
    api_key = get_settings().allsports_api_key
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10.0) as client:
            live_resp, fixtures_resp = await asyncio.gather(
                client.get(_ALLSPORTS_BASE, params={
                    "met": "Livescore",
                    "APIkey": api_key,
                }),
                client.get(_ALLSPORTS_BASE, params={
                    "met": "Fixtures",
                    "APIkey": api_key,
                    "from": today,
                    "to": today,
                }),
            )
            live_resp.raise_for_status()
            fixtures_resp.raise_for_status()

            live_raw: list[dict] = live_resp.json().get("result") or []
            fixtures_raw: list[dict] = fixtures_resp.json().get("result") or []
    except Exception:
        if _cache["data"] is not None:
            return {**_cache["data"], "stale": True}
        return {
            "live": [], "upcoming": [], "completed": [],
            "tournaments": [], "cached_at": None, "stale": True,
        }

    live_ids = {str(e.get("event_key", "")) for e in live_raw if e.get("event_key")}
    live_matches = [_transform_event(e) for e in live_raw]

    upcoming: list[dict] = []
    completed: list[dict] = []
    for e in fixtures_raw:
        if str(e.get("event_key", "")) in live_ids:
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
