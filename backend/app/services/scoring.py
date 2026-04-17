# backend/app/services/scoring.py
"""Pure scoring functions for tournament predictions.

Pick shape: {winner: str, sets_count?: int, retirement?: bool}

Scoring tiers per round: (winner_only, winner_plus_sets, winner_plus_sets_plus_retirement).

Rules:
- Wrong winner or match not played yet → 0 pts.
- Unknown round → 0 pts.
- Correct winner + actual retirement/walkover (score contains 'ret.' or 'w.o.'):
    - Predicted retirement=True → tier3 points.
    - Else → winner-only.
- Correct winner + actual normal finish:
    - Predicted retirement=True → winner-only (no retirement happened).
    - sets_count matches actual set count → tier2.
    - Else → winner-only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# (winner_only, winner_plus_sets, winner_plus_sets_plus_retirement)
ROUND_POINTS: dict[str, tuple[int, int, int]] = {
    "Q1": (2, 5, 7),
    "Q2": (3, 8, 11),
    "Q3": (3, 8, 11),
    "Q4": (4, 10, 14),
    "Q5": (4, 10, 14),
    "Q6": (5, 12, 17),
    "Qualified": (5, 12, 17),
    "R1": (5, 15, 20),
    "R2": (10, 25, 35),
    "R3": (15, 35, 50),
    "R4": (18, 40, 58),
    "QF": (20, 50, 70),
    "SF": (30, 75, 105),
    "F": (50, 100, 140),
}


@dataclass
class MatchBreakdown:
    match_id: str
    round: str
    section: str
    predicted_winner: str | None
    predicted_sets: int | None
    predicted_retirement: bool
    actual_winner: str | None
    actual_score: str | None
    points: int
    reason: str


_RET_RE = re.compile(r"ret\.?$", re.IGNORECASE)
_WO_RE = re.compile(r"^w\.?o\.?$", re.IGNORECASE)


def is_retirement(score: str | None) -> bool:
    """True if score indicates retirement or walkover."""
    if not score:
        return False
    s = score.strip()
    if _WO_RE.fullmatch(s) or s.upper() == "WO":
        return True
    return bool(_RET_RE.search(s))


def count_sets(score: str | None) -> int:
    """Count fully completed sets in a score string.

    A completed set has at least one side with >= 6 games. Tiebreak
    annotations are stripped; trailing 'ret.' is stripped. Walkover → 0.
    """
    if not score:
        return 0
    s = score.strip()
    s = re.sub(r"\s+ret\.?$", "", s, flags=re.IGNORECASE).strip()
    if _WO_RE.fullmatch(s) or s.upper() == "WO":
        return 0
    s = s.replace("-", "/")
    s = re.sub(r"\(\d+\)", "", s)
    count = 0
    for token in s.split():
        m = re.fullmatch(r"(\d+)/(\d+)", token.strip())
        if m and max(int(m.group(1)), int(m.group(2))) >= 6:
            count += 1
    return count


def compute_match_score(
    round_name: str,
    predicted_winner: str,
    actual_winner: str | None,
    predicted_sets: int | None,
    predicted_retirement: bool,
    actual_score: str | None,
) -> tuple[int, str]:
    """Score one match and return (points, short reason)."""
    if not predicted_winner:
        return 0, "no pick"
    if actual_winner is None:
        return 0, "match not played"
    if predicted_winner != actual_winner:
        return 0, "wrong winner"

    tiers = ROUND_POINTS.get(round_name)
    if tiers is None:
        return 0, "unknown round"
    t1, t2, t3 = tiers

    actual_retired = is_retirement(actual_score)

    if actual_retired:
        if predicted_retirement:
            return t3, "correct winner + retirement"
        return t1, "correct winner (retirement not predicted)"

    if predicted_retirement:
        return t1, "correct winner (match did not end in retirement)"

    if predicted_sets is None:
        return t1, "correct winner"

    actual_sets = count_sets(actual_score)
    if actual_sets == 0:
        return t1, "correct winner"
    if predicted_sets == actual_sets:
        return t2, f"correct winner + {actual_sets} sets"
    return t1, f"correct winner, wrong sets ({predicted_sets} vs {actual_sets})"


def compute_entry_breakdown(picks: dict, matches: list[dict]) -> list[MatchBreakdown]:
    """Per-match breakdown for an entry, in the order matches appear in the draw."""
    out: list[MatchBreakdown] = []
    for match in matches:
        match_id = match["id"]
        pick = picks.get(match_id) or {}
        predicted_winner = pick.get("winner") or None
        predicted_sets = pick.get("sets_count")
        if not isinstance(predicted_sets, int) or predicted_sets not in (2, 3, 4, 5):
            predicted_sets = None
        predicted_retirement = bool(pick.get("retirement"))

        if predicted_winner is None:
            points, reason = 0, "no pick"
        else:
            points, reason = compute_match_score(
                round_name=match.get("round", ""),
                predicted_winner=predicted_winner,
                actual_winner=match.get("winner"),
                predicted_sets=predicted_sets,
                predicted_retirement=predicted_retirement,
                actual_score=match.get("score"),
            )

        out.append(MatchBreakdown(
            match_id=match_id,
            round=match.get("round", ""),
            section=match.get("section", ""),
            predicted_winner=predicted_winner,
            predicted_sets=predicted_sets,
            predicted_retirement=predicted_retirement,
            actual_winner=match.get("winner"),
            actual_score=match.get("score"),
            points=points,
            reason=reason,
        ))
    return out


def compute_entry_score(picks: dict, matches: list[dict]) -> int:
    """Sum total points for an entry."""
    return sum(item.points for item in compute_entry_breakdown(picks, matches))
