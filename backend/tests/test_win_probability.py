from app.services.score_parser import LiveMatchState
from app.services.win_probability import (
    game_to_set_prob,
    implied_game_win_rate,
    implied_set_win_rate,
    live_win_probability,
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


def test_implied_game_win_rate_round_trip():
    for g in (0.3, 0.5, 0.65, 0.8):
        s = game_to_set_prob(g, 0, 0, 6)
        assert abs(implied_game_win_rate(s, 6) - g) < 1e-4


def test_implied_set_win_rate_round_trip():
    for s in (0.3, 0.5, 0.65, 0.8):
        p0 = set_to_match_prob(s, 0, 0, 2)
        assert abs(implied_set_win_rate(p0, 2) - s) < 1e-4


def test_implied_game_win_rate_symmetric_at_half():
    assert abs(implied_game_win_rate(0.5, 6) - 0.5) < 1e-4


def test_implied_set_win_rate_symmetric_at_half():
    assert abs(implied_set_win_rate(0.5, 2) - 0.5) < 1e-4


def _state(**overrides) -> LiveMatchState:
    base = dict(
        sets=[("0", "0")],
        sets_won=(0, 0),
        current_set_games=(0, 0),
        current_points=("00", "00"),
        current_points_numeric=(0, 0),
        server=1,
        is_tiebreak=False,
        games_per_set=6,
    )
    base.update(overrides)
    return LiveMatchState(**base)


def test_symmetric_rates_start_at_fifty_fifty():
    result = live_win_probability(0.5, 0.5, _state(server=None), sets_to_win=2)
    assert abs(result["p1"] - 0.5) < 1e-3
    assert abs(result["p2"] - 0.5) < 1e-3
    assert abs(result["p1"] + result["p2"] - 1.0) < 1e-9


def test_serve_bonus_favors_the_current_server():
    with_serve = live_win_probability(0.5, 0.5, _state(server=1), sets_to_win=2)
    no_serve = live_win_probability(0.5, 0.5, _state(server=None), sets_to_win=2)
    assert with_serve["p1"] > no_serve["p1"]


def test_leading_two_sets_to_love_is_near_certain():
    result = live_win_probability(
        0.55, 0.6, _state(sets_won=(2, 0), current_set_games=(0, 0), server=None),
        sets_to_win=2,
    )
    assert result["p1"] > 0.99


def test_blowout_decider_lead_swings_harder_than_early_close_game():
    blowout = live_win_probability(
        0.5, 0.5,
        _state(sets_won=(1, 1), current_set_games=(5, 2), server=1,
               current_points=("40", "15"), current_points_numeric=(3, 1)),
        sets_to_win=2,
    )
    close_early = live_win_probability(
        0.5, 0.5,
        _state(sets_won=(0, 0), current_set_games=(1, 0), server=1,
               current_points=("40", "15"), current_points_numeric=(3, 1)),
        sets_to_win=2,
    )
    assert (blowout["p1"] - 0.5) > (close_early["p1"] - 0.5)


def test_live_tiebreak_uses_real_point_score_not_coin_flip():
    near_tiebreak_win = live_win_probability(
        0.5, 0.5,
        _state(sets_won=(1, 0), current_set_games=(6, 6), server=1, is_tiebreak=True,
               current_points=("6", "2"), current_points_numeric=(6, 2)),
        sets_to_win=2,
    )
    assert near_tiebreak_win["p1"] > 0.9


def test_monotonicity_more_points_only_helps():
    behind = live_win_probability(
        0.5, 0.5,
        _state(current_points=("00", "40"), current_points_numeric=(0, 3)),
        sets_to_win=2,
    )
    ahead = live_win_probability(
        0.5, 0.5,
        _state(current_points=("40", "00"), current_points_numeric=(3, 0)),
        sets_to_win=2,
    )
    assert ahead["p1"] > behind["p1"]


def test_probabilities_always_sum_to_one():
    result = live_win_probability(
        0.62, 0.58,
        _state(sets_won=(1, 0), current_set_games=(3, 4), server=2,
               current_points=("30", "40"), current_points_numeric=(2, 3)),
        sets_to_win=2,
    )
    assert abs(result["p1"] + result["p2"] - 1.0) < 1e-9
