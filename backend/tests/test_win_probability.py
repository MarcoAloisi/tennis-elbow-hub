from app.services.win_probability import (
    point_to_game_prob,
    point_to_tiebreak_prob,
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
