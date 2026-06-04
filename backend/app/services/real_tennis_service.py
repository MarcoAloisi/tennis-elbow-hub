"""Real tennis scores service — fetches from ESPN public API, caches in memory."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

_ESPN_ATP = "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard"
_ESPN_WTA = "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard"
_HEADERS = {"Accept": "application/json"}
_CACHE_TTL = 30  # seconds
_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_fetch_lock = asyncio.Lock()


def _transform_competition(
    comp: dict, tournament_name: str, tournament_id: str, category: str, grouping: str
) -> dict | None:
    """Map an ESPN competition to our internal RealMatch shape. Returns None if malformed."""
    comp_id = comp.get("id")
    if not comp_id:
        return None

    status_raw = (comp.get("status") or {}).get("type") or {}
    state = status_raw.get("state", "pre")
    if state == "in":
        status = "live"
    elif state == "post":
        status = "completed"
    else:
        status = "upcoming"

    competitors = sorted(comp.get("competitors") or [], key=lambda c: c.get("order", 0))
    if len(competitors) < 2:
        return None

    def _name(c: dict) -> str:
        return (c.get("athlete") or {}).get("displayName", "Unknown")

    def _linescores(c: dict) -> list[int]:
        return [int(ls["value"]) for ls in (c.get("linescores") or []) if "value" in ls]

    p1_sets = _linescores(competitors[0])
    p2_sets = _linescores(competitors[1])
    sets = [[p1_sets[i], p2_sets[i]] for i in range(min(len(p1_sets), len(p2_sets)))]

    start_timestamp = None
    date_str = comp.get("date") or comp.get("startDate")
    if date_str:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            start_timestamp = int(dt.timestamp())
        except Exception:
            pass

    return {
        "id": comp_id,
        "player1": _name(competitors[0]),
        "player2": _name(competitors[1]),
        "score": {"sets": sets, "current_game": None},
        "status": status,
        "start_timestamp": start_timestamp,
        "tournament": {
            "id": tournament_id,
            "name": tournament_name,
            "category": category,
            "round": grouping,
        },
    }


def _parse_scoreboard(data: dict, category: str) -> list[dict]:
    """Flatten ESPN scoreboard response into a list of RealMatch dicts."""
    matches: list[dict] = []
    for event in data.get("events") or []:
        t_name = event.get("name", "")
        t_id = str(event.get("id", ""))
        for group in event.get("groupings") or []:
            grouping_name = (group.get("grouping") or {}).get("displayName", "")
            for comp in group.get("competitions") or []:
                match = _transform_competition(comp, t_name, t_id, category, grouping_name)
                if match:
                    matches.append(match)
    return matches


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
    """Return cached or freshly fetched real tennis scores from ESPN."""
    now = time.time()

    if _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL:
        return {**_cache["data"], "stale": False}

    async with _fetch_lock:
        now = time.time()
        if _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL:
            return {**_cache["data"], "stale": False}

        return await _do_fetch(now)


async def _do_fetch(now: float) -> dict:
    """Perform the actual HTTP fetch and update the cache."""
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10.0, follow_redirects=True) as client:
            atp_resp, wta_resp = await asyncio.gather(
                client.get(_ESPN_ATP),
                client.get(_ESPN_WTA),
            )
            atp_resp.raise_for_status()
            wta_resp.raise_for_status()
            all_matches = (
                _parse_scoreboard(atp_resp.json(), "ATP")
                + _parse_scoreboard(wta_resp.json(), "WTA")
            )
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

    live = [m for m in all_matches if m["status"] == "live"]
    upcoming = [m for m in all_matches if m["status"] == "upcoming"]
    completed = [m for m in all_matches if m["status"] == "completed"]

    data: dict = {
        "live": live,
        "upcoming": upcoming,
        "completed": completed,
        "tournaments": _extract_tournaments(all_matches),
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache["data"] = data
    _cache["fetched_at"] = now
    return {**data, "stale": False}
