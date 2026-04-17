# backend/tests/test_scoring.py
"""Unit tests for the tournament prediction scoring engine."""
from app.services.scoring import (
    compute_entry_breakdown,
    compute_entry_score,
    compute_match_score,
    count_sets,
    is_retirement,
)


class TestCountSets:
    def test_two_set_straight(self):
        assert count_sets("6/3 6/2") == 2

    def test_three_set_match(self):
        assert count_sets("6/3 3/6 7/5") == 3

    def test_tiebreak_notation(self):
        assert count_sets("7/6(3) 6/4") == 2

    def test_dash_separator(self):
        assert count_sets("6-3 6-2") == 2

    def test_empty(self):
        assert count_sets("") == 0
        assert count_sets(None) == 0

    def test_walkover(self):
        assert count_sets("WO") == 0
        assert count_sets("w.o.") == 0

    def test_retirement_drops_incomplete_set(self):
        # 2/1 is incomplete — only 6/3 counts
        assert count_sets("6/3 2/1 ret.") == 1


class TestIsRetirement:
    def test_retired(self):
        assert is_retirement("6/3 2/1 ret.") is True

    def test_walkover(self):
        assert is_retirement("WO") is True
        assert is_retirement("w.o.") is True

    def test_normal_finish(self):
        assert is_retirement("6/3 6/2") is False

    def test_none(self):
        assert is_retirement(None) is False


class TestComputeMatchScore:
    def test_wrong_winner(self):
        pts, reason = compute_match_score("R1", "A", "B", None, False, None)
        assert pts == 0
        assert reason == "wrong winner"

    def test_match_not_played(self):
        pts, reason = compute_match_score("R1", "A", None, None, False, None)
        assert pts == 0
        assert reason == "match not played"

    def test_no_pick(self):
        pts, reason = compute_match_score("R1", "", "A", None, False, None)
        assert pts == 0
        assert reason == "no pick"

    def test_winner_only(self):
        pts, reason = compute_match_score("R1", "Jira", "Jira", None, False, "6/3 6/2")
        assert pts == 5
        assert reason == "correct winner"

    def test_winner_plus_sets_r1(self):
        pts, reason = compute_match_score("R1", "Jira", "Jira", 2, False, "6/3 6/2")
        assert pts == 15
        assert "2 sets" in reason

    def test_winner_plus_sets_final(self):
        pts, reason = compute_match_score("F", "Jira", "Jira", 3, False, "6/3 3/6 7/5")
        assert pts == 100
        assert "3 sets" in reason

    def test_winner_wrong_sets_count(self):
        pts, reason = compute_match_score("R1", "Jira", "Jira", 2, False, "6/3 3/6 6/4")
        assert pts == 5
        assert "wrong sets" in reason

    def test_retirement_predicted_and_happened(self):
        pts, reason = compute_match_score("SF", "Jira", "Jira", None, True, "6/3 2/1 ret.")
        assert pts == 105  # SF tier3
        assert "retirement" in reason.lower()

    def test_retirement_predicted_but_no_retirement(self):
        pts, reason = compute_match_score("R1", "Jira", "Jira", None, True, "6/3 6/2")
        assert pts == 5

    def test_retirement_happened_but_not_predicted(self):
        pts, reason = compute_match_score("R2", "Jira", "Jira", 3, False, "6/3 2/1 ret.")
        assert pts == 10  # R2 winner-only

    def test_walkover_counts_as_retirement(self):
        pts, reason = compute_match_score("R1", "Jira", "Jira", None, True, "WO")
        assert pts == 20  # R1 tier3
        assert "retirement" in reason.lower()

    def test_unknown_round(self):
        pts, reason = compute_match_score("R99", "Jira", "Jira", 2, False, "6/3 6/2")
        assert pts == 0


class TestComputeEntryScore:
    def test_two_correct_picks(self):
        picks = {
            "main_R1_0": {"winner": "Jira", "sets_count": 2},
            "main_R1_1": {"winner": "gifu"},
        }
        matches = [
            {"id": "main_R1_0", "section": "main", "round": "R1", "winner": "Jira", "score": "6/3 6/2"},
            {"id": "main_R1_1", "section": "main", "round": "R1", "winner": "gifu", "score": "6/4 6/1"},
        ]
        # R1 tier2 (winner+sets) = 15, R1 tier1 (winner only) = 5
        assert compute_entry_score(picks, matches) == 15 + 5

    def test_unknown_match_id_ignored(self):
        picks = {"nonexistent": {"winner": "Jira"}}
        matches: list[dict] = []
        assert compute_entry_score(picks, matches) == 0


class TestComputeEntryBreakdown:
    def test_breakdown_items_per_match(self):
        picks = {
            "main_R1_0": {"winner": "Jira", "sets_count": 2},
            "main_R1_1": {"winner": "B", "retirement": True},
        }
        matches = [
            {"id": "main_R1_0", "section": "main", "round": "R1", "winner": "Jira", "score": "6/3 6/2"},
            {"id": "main_R1_1", "section": "main", "round": "R1", "winner": "B", "score": "6/4 3/0 ret."},
        ]
        items = compute_entry_breakdown(picks, matches)
        assert len(items) == 2
        assert items[0].points == 15
        assert items[0].predicted_sets == 2
        assert items[1].points == 20  # R1 tier3
        assert items[1].predicted_retirement is True
