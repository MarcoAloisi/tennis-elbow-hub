"""Tests for real tennis service and endpoint."""

from fastapi.testclient import TestClient


def _make_event(key, status, home, away, result="-", league="ATP - Roland Garros",
                league_key=1, round_name="Quarter-finals"):
    return {
        "event_key": key,
        "event_date": "2026-06-05",
        "event_time": "10:00",
        "event_home_team": home,
        "event_away_team": away,
        "event_final_result": result,
        "event_status": status,
        "league_name": league,
        "league_key": league_key,
        "league_round": round_name,
    }


class TestTransformEvent:
    def test_live_match(self):
        from app.services.real_tennis_service import _transform_event
        e = _make_event(123, "2nd Set", "Djokovic", "Alcaraz", "6-4")
        result = _transform_event(e)
        assert result["id"] == "123"
        assert result["player1"] == "Djokovic"
        assert result["player2"] == "Alcaraz"
        assert result["status"] == "live"
        assert result["score"]["sets"] == [[6, 4]]
        assert result["tournament"]["name"] == "Roland Garros"
        assert result["tournament"]["category"] == "ATP"
        assert result["tournament"]["round"] == "Quarter-finals"

    def test_upcoming_match_has_empty_sets(self):
        from app.services.real_tennis_service import _transform_event
        e = _make_event(456, "notstarted", "Swiatek", "Gauff", "-", "WTA - Roland Garros")
        result = _transform_event(e)
        assert result["status"] == "upcoming"
        assert result["score"]["sets"] == []
        assert result["tournament"]["category"] == "WTA"

    def test_completed_match(self):
        from app.services.real_tennis_service import _transform_event
        e = _make_event(789, "Finished", "Federer", "Nadal", "6-4 3-6 6-4")
        result = _transform_event(e)
        assert result["status"] == "completed"
        assert result["score"]["sets"] == [[6, 4], [3, 6], [6, 4]]

    def test_missing_player_defaults_to_unknown(self):
        from app.services.real_tennis_service import _transform_event
        e = _make_event(999, "notstarted", None, None, "-")
        result = _transform_event(e)
        assert result["player1"] == "Unknown"
        assert result["player2"] == "Unknown"


class TestParseSets:
    def test_two_sets(self):
        from app.services.real_tennis_service import _parse_sets
        assert _parse_sets("6-4 7-5") == [[6, 4], [7, 5]]

    def test_three_sets(self):
        from app.services.real_tennis_service import _parse_sets
        assert _parse_sets("6-4 3-6 6-3") == [[6, 4], [3, 6], [6, 3]]

    def test_empty_result(self):
        from app.services.real_tennis_service import _parse_sets
        assert _parse_sets("-") == []
        assert _parse_sets("") == []


class TestExtractTournaments:
    def test_groups_by_tournament_id(self):
        from app.services.real_tennis_service import _extract_tournaments
        matches = [
            {"tournament": {"id": 1, "name": "Wimbledon", "category": "ATP", "round": "QF"}},
            {"tournament": {"id": 1, "name": "Wimbledon", "category": "ATP", "round": "QF"}},
            {"tournament": {"id": 2, "name": "US Open", "category": "WTA", "round": "R1"}},
        ]
        result = _extract_tournaments(matches)
        assert len(result) == 2
        wimbledon = next(t for t in result if t["id"] == 1)
        assert wimbledon["match_count"] == 2

    def test_sorted_by_match_count_descending(self):
        from app.services.real_tennis_service import _extract_tournaments
        matches = [
            {"tournament": {"id": 2, "name": "US Open", "category": "WTA", "round": "R1"}},
            {"tournament": {"id": 1, "name": "Wimbledon", "category": "ATP", "round": "QF"}},
            {"tournament": {"id": 1, "name": "Wimbledon", "category": "ATP", "round": "QF"}},
        ]
        result = _extract_tournaments(matches)
        assert result[0]["id"] == 1

    def test_empty_input_returns_empty_list(self):
        from app.services.real_tennis_service import _extract_tournaments
        assert _extract_tournaments([]) == []


class TestRealTennisEndpoint:
    def test_endpoint_returns_correct_shape(self, client: TestClient) -> None:
        from unittest.mock import AsyncMock, patch

        mock_data = {
            "live": [],
            "upcoming": [],
            "completed": [],
            "tournaments": [],
            "cached_at": "2026-06-04T12:00:00+00:00",
            "stale": False,
        }
        with patch(
            "app.api.endpoints.real_tennis.fetch_real_tennis_scores",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            response = client.get("/api/real-tennis/scores")

        assert response.status_code == 200
        data = response.json()
        for key in ("live", "upcoming", "completed", "tournaments", "stale"):
            assert key in data
        assert isinstance(data["live"], list)
        assert isinstance(data["upcoming"], list)
        assert isinstance(data["completed"], list)
        assert isinstance(data["tournaments"], list)

    def test_endpoint_propagates_stale_flag(self, client: TestClient) -> None:
        from unittest.mock import AsyncMock, patch

        mock_data = {
            "live": [],
            "upcoming": [],
            "completed": [],
            "tournaments": [],
            "cached_at": None,
            "stale": True,
        }
        with patch(
            "app.api.endpoints.real_tennis.fetch_real_tennis_scores",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            response = client.get("/api/real-tennis/scores")

        assert response.status_code == 200
        assert response.json()["stale"] is True
