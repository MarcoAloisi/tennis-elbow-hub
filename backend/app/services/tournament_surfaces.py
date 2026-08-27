"""Tournament name -> surface inference.

Ported from the frontend's tournaments.json (mirrored at
app/data/tournaments.json) so GameServer.surface_display agrees with the
frontend's own surface badge icon (surfaceInfo in MatchCard.vue) instead
of defaulting every non-Slam tournament to hard court.
"""

import json
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "tournaments.json"

SURFACE_DISPLAY_NAMES = {
    "hard": "Hard Court",
    "clay": "Clay Court",
    "grass": "Grass Court",
    "indoor": "Indoor Hard",
}

_TOURNAMENT_CATEGORIES = (
    "grandSlams", "masters1000", "atp500", "atp250", "atpFinals", "challengers",
)


def _load() -> tuple[dict[str, str], dict[str, list[str]]]:
    data: dict[str, Any] = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    tournament_surfaces: dict[str, str] = {}
    for category in _TOURNAMENT_CATEGORIES:
        for tour_name, surface in data.get(category, {}).items():
            tournament_surfaces[tour_name.lower()] = surface
    keywords: dict[str, list[str]] = data.get("keywords", {})
    return tournament_surfaces, keywords


_TOURNAMENT_SURFACES, _KEYWORDS = _load()


def infer_surface(name: str) -> str | None:
    """Best-effort surface ('hard'/'clay'/'grass'/'indoor') for a
    tournament name, or None if nothing matches. Mirrors the frontend's
    surfaceInfo lookup order: explicit tournament name match first
    (checked in the same category order as tournaments.json), then
    keyword substring match."""
    name_lower = name.lower()

    for tour_name, surface in _TOURNAMENT_SURFACES.items():
        if tour_name in name_lower:
            return surface

    for surface, kws in _KEYWORDS.items():
        for kw in kws:
            if kw.lower() in name_lower:
                return surface

    return None
