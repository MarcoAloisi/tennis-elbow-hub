from datetime import date

from app.services.stats_service import _h2h_from_rows


def _appearance(name, opponent, result, surface="Clay", mod="vanilla", day="2026-08-01"):
    return {
        "name": name,
        "opponent": opponent,
        "result": result,
        "surface": surface,
        "mod": mod,
        "date": date.fromisoformat(day),
    }


def test_no_history_is_empty_record():
    record = _h2h_from_rows("Alice", "Bob", [])
    assert record.total == 0
    assert record.wins_a == 0
    assert record.wins_b == 0
    assert record.specific_total == 0


def test_counts_wins_from_both_directions_of_the_same_match():
    appearances = [
        _appearance("Alice", "Bob", "W"),
        _appearance("Bob", "Alice", "L"),
    ]
    record = _h2h_from_rows("Alice", "Bob", appearances)
    assert record.wins_a == 1
    assert record.wins_b == 0
    assert record.total == 1


def test_ignores_matches_against_other_opponents():
    appearances = [
        _appearance("Alice", "Bob", "W"),
        _appearance("Alice", "Carol", "L"),
    ]
    record = _h2h_from_rows("Alice", "Bob", appearances)
    assert record.total == 1


def test_surface_and_mod_specific_breakdown():
    appearances = [
        _appearance("Alice", "Bob", "W", surface="Clay", mod="vanilla"),
        _appearance("Alice", "Bob", "L", surface="Grass", mod="vanilla"),
        _appearance("Alice", "Bob", "W", surface="Clay", mod="vanilla"),
    ]
    record = _h2h_from_rows("Alice", "Bob", appearances, surface="Clay", mod="vanilla")
    assert record.total == 3
    assert record.specific_total == 2
    assert record.specific_wins_a == 2
    assert record.specific_wins_b == 0


def test_no_surface_mod_filter_leaves_specific_at_zero():
    appearances = [_appearance("Alice", "Bob", "W")]
    record = _h2h_from_rows("Alice", "Bob", appearances)
    assert record.specific_total == 0
