from app.services.score_parser import parse_live_state


def test_unparseable_returns_none():
    assert parse_live_state("", 6) is None
    assert parse_live_state("garbage", 6) is None


def test_no_set_segments_returns_none():
    assert parse_live_state(" -- 00:40", 6) is None


def test_mid_set_score():
    state = parse_live_state("6/3 4/6 1/1 -- 00:40•", 6)
    assert state is not None
    assert state.sets == [("6", "3"), ("4", "6"), ("1", "1")]
    assert state.sets_won == (1, 1)
    assert state.current_set_games == (1, 1)
    assert state.current_points == ("00", "40")
    assert state.current_points_numeric == (0, 3)
    assert state.server == 2
    assert state.is_tiebreak is False
    assert state.games_per_set == 6


def test_server_marker_on_p1_side():
    state = parse_live_state("6/3 -- •40:15", 6)
    assert state.server == 1
    assert state.current_points == ("40", "15")


def test_deuce():
    state = parse_live_state("0/0 -- 40:40", 6)
    assert state.current_points_numeric == (3, 3)


def test_advantage_p1():
    state = parse_live_state("0/0 -- 40:Ad", 6)
    assert state.current_points_numeric == (3, 4)


def test_advantage_p2():
    state = parse_live_state("0/0 -- Ad:40", 6)
    assert state.current_points_numeric == (4, 3)


def test_tiebreak_point_counts_as_raw_ints():
    state = parse_live_state("6/6 -- 3:5•", 6)
    assert state.is_tiebreak is True
    assert state.current_points_numeric == (3, 5)
    assert state.server == 2


def test_no_current_game_segment():
    state = parse_live_state("0/0 -- ", 6)
    assert state.current_points is None
    assert state.current_points_numeric is None


def test_games_per_set_zero_falls_back_to_six():
    state = parse_live_state("6/3 -- 00:40", 0)
    assert state.games_per_set == 6


def test_first_set_win_counted():
    state = parse_live_state("6/3 -- 00:40", 6)
    assert state.sets_won == (1, 0)
    assert state.current_set_games == (0, 0)
