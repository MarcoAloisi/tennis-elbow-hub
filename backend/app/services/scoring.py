# backend/app/services/scoring.py
"""Pure scoring functions for tournament predictions.

Scoring rules:
- Wrong winner → 0 pts
- Match not played yet → 0 pts
- Qualifying rounds (Q1, Q2, Qualified) → 0 pts (not scored)
- Unknown/unrecognised round names → 0 pts
- Correct winner, no score / unparseable → winner-only base pts
- Correct sets count + all sets exact → exact score pts
- Correct sets count + some sets exact → sets-count pts + 3 per correct set
- Wrong sets count + some sets match → winner-only pts + 3 per correct set

Note: super-tiebreak sets (e.g. 10/7) pass the valid-set filter (max >= 6)
and are treated as normal sets for scoring purposes.
"""

from __future__ import annotations

import re

# (winner_only, correct_sets_count, exact_score)
ROUND_POINTS: dict[str, tuple[int, int, int]] = {
    "Q1": (2, 5, 10),
    "Q2": (3, 8, 15),
    "Q3": (3, 8, 15),
    "Q4": (4, 10, 20),
    "Q5": (4, 10, 20),
    "Q6": (5, 12, 25),
    "Qualified": (5, 12, 25),
    "R1": (5, 15, 30),
    "R2": (10, 25, 50),
    "R3": (15, 35, 70),
    "R4": (18, 40, 80),
    "QF": (20, 50, 100),
    "SF": (30, 75, 150),
    "F": (50, 100, 200),
}

# Rounds that are NOT scored
_UNSCORED_ROUNDS: set[str] = set()


def parse_score(score: str | None) -> list[str]:
    """Parse a score string into a list of normalised set scores.

    Handles formats like '6/3 6/2', '6-3 6-2', '7/6(3) 6/4', '6/3 2/1 ret.'.
    Tiebreak annotations (e.g. '(3)') are stripped for comparison.
    Walkover / w.o. / WO returns [].
    Only fully completed sets are returned (ret. mid-set is dropped).
    A completed set has at least one player reaching 6 or more games.

    Args:
        score: Raw score string from managames or user input.

    Returns:
        List of normalised set score strings like ['6/3', '7/6', '3/6'].
    """
    if not score:
        return []

    score = score.strip()

    # Strip ret./retirement suffix — keep only what came before
    score = re.sub(r"\s+ret\.?$", "", score, flags=re.IGNORECASE).strip()

    # Walkover / w.o. — no sets
    if re.fullmatch(r"w\.?o\.?", score, re.IGNORECASE) or score.upper() == "WO":
        return []

    # Normalise: replace dashes with slashes, strip tiebreak annotations
    score = score.replace("-", "/")
    score = re.sub(r"\(\d+\)", "", score)  # remove (3), (6) etc.

    sets = []
    for token in score.split():
        token = token.strip()
        if re.fullmatch(r"\d+/\d+", token):
            a, b = int(token.split("/")[0]), int(token.split("/")[1])
            # Only include completed sets: at least one player reached 6+ games
            if max(a, b) >= 6:
                sets.append(token)

    return sets


def compute_match_score(
    round_name: str,
    predicted_winner: str,
    actual_winner: str | None,
    predicted_score: str | None,
    actual_score: str | None,
) -> int:
    """Compute points for one match prediction.

    Args:
        round_name: e.g. 'R1', 'QF', 'F'. Qualifying rounds score 0.
        predicted_winner: Nickname the user picked to win.
        actual_winner: Actual winner from managames (None if not played).
        predicted_score: User-provided score string (may be None).
        actual_score: Actual score from managames (None if not played).

    Returns:
        Points earned for this match (0 if wrong winner or not yet played).
    """
    if round_name in _UNSCORED_ROUNDS:
        return 0
    if actual_winner is None:
        return 0
    if predicted_winner != actual_winner:
        return 0

    round_pts = ROUND_POINTS.get(round_name)
    if round_pts is None:
        return 0  # unrecognised round — no points
    pts_winner, pts_sets, pts_exact = round_pts

    pred_sets = parse_score(predicted_score)
    actual_sets = parse_score(actual_score)

    if not pred_sets or not actual_sets:
        return pts_winner

    # Per-set partial credit
    per_set_bonus = sum(3 for p, a in zip(pred_sets, actual_sets) if p == a)

    if pred_sets == actual_sets:
        return pts_exact  # exact match — max points

    if len(pred_sets) == len(actual_sets):
        # Correct sets count, not exact
        return pts_sets + per_set_bonus

    # Wrong sets count — winner only + partial
    return pts_winner + per_set_bonus


def compute_entry_score(picks: dict, matches: list[dict]) -> int:
    """Compute total score for a prediction entry against actual draw results.

    Args:
        picks: {match_id: {"winner": str, "score": str | None}}
        matches: draw_data["matches"] list from PredictionTournament.

    Returns:
        Total points earned across all predicted matches.
    """
    match_map = {m["id"]: m for m in matches}
    total = 0
    for match_id, pick in picks.items():
        match = match_map.get(match_id)
        if not match:
            continue
        total += compute_match_score(
            round_name=match["round"],
            predicted_winner=pick.get("winner", ""),
            actual_winner=match.get("winner"),
            predicted_score=pick.get("score"),
            actual_score=match.get("score"),
        )
    return total
