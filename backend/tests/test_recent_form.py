from datetime import date

from app.services.stats_service import _recent_form_win_rate


def _appearance(result, day):
    return {"result": result, "date": date.fromisoformat(day)}


def test_no_matches_returns_none():
    assert _recent_form_win_rate([], today=date(2026, 8, 26)) is None


def test_matches_outside_window_are_excluded():
    old = [_appearance("W", "2026-01-01")]
    assert _recent_form_win_rate(old, today=date(2026, 8, 26)) is None


def test_win_rate_within_window():
    appearances = [
        _appearance("W", "2026-08-20"),
        _appearance("W", "2026-08-15"),
        _appearance("L", "2026-08-10"),
    ]
    rate = _recent_form_win_rate(appearances, today=date(2026, 8, 26))
    assert abs(rate - (2 / 3)) < 1e-9


def test_unknown_results_are_excluded_from_the_denominator():
    appearances = [
        _appearance("W", "2026-08-20"),
        _appearance("?", "2026-08-15"),
    ]
    rate = _recent_form_win_rate(appearances, today=date(2026, 8, 26))
    assert rate == 1.0
