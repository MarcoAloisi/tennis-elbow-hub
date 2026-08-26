from app.services.win_probability import (
    game_to_set_prob,
    point_to_game_prob,
    point_to_tiebreak_prob,
    set_to_match_prob,
)


def test_symmetric_point_rate_is_fifty_fifty():
    assert point_to_game_prob(0.5, 0, 0) == 0.5
    assert point_to_tiebreak_prob(0.5, 0, 0) == 0.5


def test_game_win_from_match_point():
    # 40-0 (3-0): one more point at p=0.5 doesn't guarantee it, but a
    # dominant p should push the win prob close to 1.
    assert point_to_game_prob(0.9, 3, 0) > 0.9


def test_game_deuce_is_symmetric_closed_form():
    # At exactly deuce (3-3) with p=0.5, win prob is 0.5 regardless of path.
    assert abs(point_to_game_prob(0.5, 3, 3) - 0.5) < 1e-9


def test_game_advantage_beats_deuce():
    # Advantage-in (4-3) is a strictly better position than deuce (3-3).
    p = 0.6
    assert point_to_game_prob(p, 4, 3) > point_to_game_prob(p, 3, 3)


def test_game_recursion_terminates_from_advantage_state():
    # Regression: a naive recursion that only special-cases the exact
    # (target-1, target-1) tied state recurses forever from (4,3) -> (4,4)
    # -> (5,5) -> ... because those re-tied states are never (3,3) again.
    # This must resolve instantly and be a valid probability.
    result = point_to_game_prob(0.5, 4, 3)
    assert 0.0 <= result <= 1.0


def test_tiebreak_win_from_match_point():
    assert point_to_tiebreak_prob(0.9, 6, 2) > 0.99


def test_game_and_tiebreak_share_the_same_recursion_shape():
    # Different targets (4 vs 7), same win-by-2 structure.
    assert point_to_game_prob(0.7, 0, 0) != point_to_tiebreak_prob(0.7, 0, 0)


def test_symmetric_game_rate_set_is_fifty_fifty():
    assert game_to_set_prob(0.5, 0, 0, 6) == 0.5


def test_set_win_from_five_love():
    assert game_to_set_prob(0.5, 5, 0, 6) > 0.95


def test_set_terminal_case_at_games_all_uses_g_as_tiebreak_stand_in():
    # At 6-6, the set is decided by one Bernoulli(g) "trial" — a stand-in
    # for the hypothetical, not-yet-reached tiebreak.
    assert game_to_set_prob(0.7, 6, 6, 6) == 0.7


def test_set_does_not_go_past_games_per_set_plus_one():
    # 7-5 is a legal, terminal, no-tiebreak set win — must not recurse
    # toward 8-6 or beyond.
    p = game_to_set_prob(0.5, 7, 5, 6)
    assert p == 1.0


def test_non_default_games_per_set_changes_terminal_case():
    # A match configured for a shorter set (e.g. games_per_set=4) must use
    # that value, not a hardcoded 6. g=0.5 is deliberately NOT used here: at
    # a symmetric point-win-rate, (3,3) resolves to exactly 0.5 whether it's
    # the games_per_set=4 terminal case OR a mid-recursion tied state in a
    # games_per_set=6 set (by the same complementary-symmetry argument as
    # the deuce closed form) — the two would coincidentally match and this
    # test would not actually be checking what its name claims.
    short_set = game_to_set_prob(0.65, 3, 3, 4)
    long_set = game_to_set_prob(0.65, 3, 3, 6)
    assert short_set != long_set


def test_symmetric_set_rate_match_is_fifty_fifty():
    assert set_to_match_prob(0.5, 0, 0, 2) == 0.5


def test_match_win_from_two_sets_up_in_best_of_three():
    assert set_to_match_prob(0.5, 2, 0, 2) == 1.0


def test_best_of_five_needs_three_sets():
    assert set_to_match_prob(0.5, 2, 0, 3) < 1.0
