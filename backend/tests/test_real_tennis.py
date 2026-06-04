"""Tests for real tennis service and endpoint."""

from fastapi.testclient import TestClient


def _make_comp(comp_id, state, p1_name, p2_name, p1_sets, p2_sets, date_str="2026-06-04T10:00Z"):
    return {
        "id": comp_id,
        "date": date_str,
        "status": {"type": {"state": state}},
        "competitors": [
            {
                "order": 1,
                "athlete": {"displayName": p1_name},
                "linescores": [{"value": float(s)} for s in p1_sets],
            },
            {
                "order": 2,
                "athlete": {"displayName": p2_name},
                "linescores": [{"value": float(s)} for s in p2_sets],
            },
        ],
    }


class TestTransformCompetition:
    def test_live_match(self):
        from app.services.real_tennis_service import _transform_competition
        comp = _make_comp("123", "in", "Djokovic", "Alcaraz", [6, 7], [4, 5])
        result = _transform_competition(comp, "Wimbledon", "1", "ATP", "Men's Singles")
        assert result["id"] == "123"
        assert result["player1"] == "Djokovic"
        assert result["player2"] == "Alcaraz"
        assert result["status"] == "live"
        assert result["score"]["sets"] == [[6, 4], [7, 5]]
        assert result["score"]["current_game"] is None
        assert result["tournament"]["name"] == "Wimbledon"
        assert result["tournament"]["category"] == "ATP"
        assert result["tournament"]["round"] == "Men's Singles"

    def test_upcoming_match_has_empty_sets(self):
        from app.services.real_tennis_service import _transform_competition
        comp = _make_comp("456", "pre", "Swiatek", "Gauff", [], [])
        result = _transform_competition(comp, "Roland Garros", "2", "WTA", "Women's Singles")
        assert result["status"] == "upcoming"
        assert result["score"]["sets"] == []

    def test_completed_match(self):
        from app.services.real_tennis_service import _transform_competition
        comp = _make_comp("789", "post", "Federer", "Nadal", [6, 3, 6], [4, 6, 4])
        result = _transform_competition(comp, "Wimbledon", "1", "ATP", "Men's Singles")
        assert result["status"] == "completed"
        assert result["score"]["sets"] == [[6, 4], [3, 6], [6, 4]]

    def test_missing_id_returns_none(self):
        from app.services.real_tennis_service import _transform_competition
        comp = {"status": {"type": {"state": "pre"}}, "competitors": [
            {"order": 1, "athlete": {"displayName": "A"}, "linescores": []},
            {"order": 2, "athlete": {"displayName": "B"}, "linescores": []},
        ]}
        assert _transform_competition(comp, "T", "1", "ATP", "Singles") is None

    def test_fewer_than_two_competitors_returns_none(self):
        from app.services.real_tennis_service import _transform_competition
        comp = {"id": "99", "status": {"type": {"state": "pre"}}, "competitors": [
            {"order": 1, "athlete": {"displayName": "A"}, "linescores": []},
        ]}
        assert _transform_competition(comp, "T", "1", "ATP", "Singles") is None


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
