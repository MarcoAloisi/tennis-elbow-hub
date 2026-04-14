# backend/tests/test_scoring.py
"""Unit tests for the tournament prediction scoring engine."""
from app.services.scoring import compute_match_score, compute_entry_score, parse_score, ROUND_POINTS


class TestParseScore:
    def test_two_set_straight(self):
        assert parse_score("6/3 6/2") == ["6/3", "6/2"]

    def test_three_set_match(self):
        assert parse_score("6/3 3/6 7/5") == ["6/3", "3/6", "7/5"]

    def test_tiebreak_notation_stripped(self):
        # 7/6(3) normalises to 7/6 for comparison
        assert parse_score("7/6(3) 6/4") == ["7/6", "6/4"]

    def test_dash_separator(self):
        assert parse_score("6-3 6-2") == ["6/3", "6/2"]

    def test_empty_string(self):
        assert parse_score("") == []

    def test_none(self):
        assert parse_score(None) == []

    def test_walkover_returns_empty(self):
        assert parse_score("WO") == []
        assert parse_score("w.o.") == []

    def test_retired_returns_partial(self):
        # ret. / ret scores still count the completed sets
        assert parse_score("6/3 2/1 ret.") == ["6/3"]


class TestComputeMatchScore:
    def test_wrong_winner_zero(self):
        assert compute_match_score("R1", "PlayerA", "PlayerB", None, None) == 0

    def test_match_not_played_zero(self):
        assert compute_match_score("R1", "PlayerA", None, None, None) == 0

    def test_winner_only_no_score(self):
        assert compute_match_score("R1", "Jira", "Jira", None, None) == 5
        assert compute_match_score("SF", "Jira", "Jira", None, None) == 30
        assert compute_match_score("F", "Jira", "Jira", None, None) == 50

    def test_winner_with_unparseable_score(self):
        assert compute_match_score("R1", "Jira", "Jira", "WO", "6/3 6/2") == 5

    def test_exact_score_r1(self):
        assert compute_match_score("R1", "Jira", "Jira", "6/3 6/2", "6/3 6/2") == 30

    def test_exact_score_final(self):
        assert compute_match_score("F", "Jira", "Jira", "6/3 3/6 7/5", "6/3 3/6 7/5") == 200

    def test_correct_sets_count_straight(self):
        # predicted 2 sets, actual 2 sets — correct sets count
        score = compute_match_score("R1", "Jira", "Jira", "6/1 6/0", "6/3 6/2")
        assert score == 15  # sets count pts, no individual set bonus (both wrong)

    def test_correct_sets_count_plus_partial(self):
        # predicted 6/3 3/6 7/5, actual 6/3 3/6 6/1 — correct sets count, 2 sets right
        score = compute_match_score("SF", "Jira", "Jira", "6/3 3/6 7/5", "6/3 3/6 6/1")
        assert score == 75 + 3 + 3  # sets pts + 2 correct sets * 3

    def test_wrong_sets_count_winner_only_plus_partial(self):
        # predicted 2 sets, actual 3 sets — wrong sets count
        score = compute_match_score("R1", "Jira", "Jira", "6/3 6/2", "6/3 3/6 6/4")
        assert score == 5 + 3  # winner pts + 1 correct set (6/3)

    def test_tiebreak_normalized_in_comparison(self):
        # 7/6 should match 7/6(3)
        score = compute_match_score("QF", "Jira", "Jira", "7/6 6/4", "7/6(3) 6/4")
        assert score == 100  # exact

    def test_qualifying_round_scores_zero(self):
        # Q1, Q2, Qualified are not scored
        assert compute_match_score("Q2", "Jira", "Jira", None, None) == 0
        assert compute_match_score("Q1", "Jira", "Jira", None, None) == 0

    def test_unrecognised_round_scores_zero(self):
        # Unknown round names should not award points
        assert compute_match_score("R4", "Jira", "Jira", None, None) == 0


class TestComputeEntryScore:
    def test_two_correct_picks(self):
        picks = {
            "main_R1_0": {"winner": "Jira", "score": "6/3 6/2"},
            "main_R1_1": {"winner": "gifu", "score": None},
        }
        matches = [
            {"id": "main_R1_0", "round": "R1", "winner": "Jira", "score": "6/3 6/2"},
            {"id": "main_R1_1", "round": "R1", "winner": "gifu", "score": "6/4 6/1"},
        ]
        # R1 exact = 30, R1 winner only = 5
        assert compute_entry_score(picks, matches) == 30 + 5

    def test_unknown_match_id_ignored(self):
        picks = {"nonexistent_match": {"winner": "Jira"}}
        matches = []
        assert compute_entry_score(picks, matches) == 0
