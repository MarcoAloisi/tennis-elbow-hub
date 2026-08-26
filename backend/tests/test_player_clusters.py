"""Unit tests for ELO clustering helpers — no database."""

from datetime import date

from app.services.stats_service import (
    ELO_BAND,
    cluster_list_rows,
    empty_player_details,
    _details_from_matches,
    _pick_cluster,
    _split_elo_clusters,
)


def _m(elo: int, result: str = "W", day: str | None = "2026-08-01", opponent_elo: int = 1500) -> dict:
    return {
        "opponent": "X",
        "score": "6/4",
        "date": day,
        "player_elo": elo,
        "opponent_elo": opponent_elo,
        "result": result,
    }


def test_elo_band_is_200():
    assert ELO_BAND == 200


def test_split_two_disjoint_groups():
    matches = [_m(1200), _m(1220), _m(2100), _m(2120)]
    clusters = _split_elo_clusters(matches)
    elos = [sorted(m["player_elo"] for m in c) for c in clusters]
    assert elos == [[1200, 1220], [2100, 2120]]


def test_split_climber_stays_one_cluster():
    matches = [_m(e) for e in (1200, 1400, 1600, 1800, 2000, 2100)]
    clusters = _split_elo_clusters(matches)
    assert len(clusters) == 1
    assert len(clusters[0]) == 6


def test_split_gap_exactly_200_stays_connected():
    # 1200 and 1400 differ by 200 → same cluster
    clusters = _split_elo_clusters([_m(1200), _m(1400)])
    assert len(clusters) == 1


def test_split_gap_201_splits():
    clusters = _split_elo_clusters([_m(1200), _m(1401)])
    assert len(clusters) == 2


def test_pick_cluster_by_live_elo():
    low = [_m(1200), _m(1220)]
    high = [_m(2100), _m(2120)]
    clusters = [low, high]
    picked = _pick_cluster(clusters, 2110)
    assert {m["player_elo"] for m in picked} == {2100, 2120}
    picked_low = _pick_cluster(clusters, 1210)
    assert {m["player_elo"] for m in picked_low} == {1200, 1220}


def test_pick_cluster_empty_when_far():
    clusters = [_split_elo_clusters([_m(2100), _m(2120)])[0]]
    assert _pick_cluster(clusters, 1200) == []


def test_pick_cluster_tie_prefers_more_matches():
    a = [_m(1300)]
    b = [_m(1500), _m(1510)]
    # 1400 is 100 from both intervals [1300,1300] and [1500,1510]
    picked = _pick_cluster([a, b], 1400)
    assert len(picked) == 2


def test_cluster_list_rows_splits_same_name():
    rows = cluster_list_rows(
        [
            {"name": "Ambience", "player_elo": 1200, "date": date(2026, 1, 1)},
            {"name": "Ambience", "player_elo": 1220, "date": date(2026, 1, 2)},
            {"name": "Ambience", "player_elo": 2100, "date": date(2026, 2, 1)},
            {"name": "Other", "player_elo": 1500, "date": date(2026, 1, 1)},
        ]
    )
    ambi = [r for r in rows if r["name"] == "Ambience"]
    assert len(ambi) == 2
    elos = sorted(r["latest_elo"] for r in ambi)
    assert elos == [1220, 2100]
    low = next(r for r in ambi if r["latest_elo"] == 1220)
    assert low["total_matches"] == 2
    assert low["last_match_date"] == "2026-01-02"


def test_empty_player_details_has_no_error_key():
    out = empty_player_details("Ambience")
    assert out["name"] == "Ambience"
    assert out["total_matches"] == 0
    assert out["wins"] == 0
    assert out["recent_matches"] == []
    assert "error" not in out


def test_details_from_matches_recomputes_wl():
    matches = [
        _m(2100, "W", "2026-08-20", 2200),
        _m(2080, "L", "2026-08-10", 1000),
        _m(2090, "W", "2026-07-01", 1800),
    ]
    out = _details_from_matches("Ambience", matches, today=date(2026, 8, 25))
    assert out["wins"] == 2
    assert out["losses"] == 1
    assert out["total_matches"] == 3
    assert out["win_rate"] == 66.7
    assert out["matches_last_7_days"] == 1
    assert out["matches_last_30_days"] == 2
    assert out["best_win"]["opponent_elo"] == 2200
    assert out["worst_loss"]["opponent_elo"] == 1000
    assert len(out["recent_matches"]) == 3
    assert "error" not in out
