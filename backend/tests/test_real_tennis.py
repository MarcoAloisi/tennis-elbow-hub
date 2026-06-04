"""Tests for real tennis service and endpoint."""

from fastapi.testclient import TestClient


class TestTransformEvent:
    def test_live_match(self):
        from app.services.real_tennis_service import _transform_event
        raw = {
            "id": 123,
            "tournament": {
                "id": 1,
                "name": "Wimbledon",
                "category": {"name": "ATP"},
            },
            "roundInfo": {"name": "Quarter-finals"},
            "homeTeam": {"name": "Djokovic"},
            "awayTeam": {"name": "Alcaraz"},
            "homeScore": {"period1": 6, "period2": 7},
            "awayScore": {"period1": 4, "period2": 5},
            "status": {"type": "inprogress"},
            "startTimestamp": 1234567890,
        }
        result = _transform_event(raw)
        assert result["id"] == 123
        assert result["player1"] == "Djokovic"
        assert result["player2"] == "Alcaraz"
        assert result["status"] == "live"
        assert result["score"]["sets"] == [[6, 4], [7, 5]]
        assert result["score"]["current_game"] is None
        assert result["tournament"]["name"] == "Wimbledon"
        assert result["tournament"]["round"] == "Quarter-finals"
        assert result["tournament"]["category"] == "ATP"

    def test_upcoming_match_has_empty_sets(self):
        from app.services.real_tennis_service import _transform_event
        raw = {
            "id": 456,
            "tournament": {"id": 2, "name": "US Open", "category": {"name": "WTA"}},
            "roundInfo": {"name": "Round 1"},
            "homeTeam": {"name": "Swiatek"},
            "awayTeam": {"name": "Gauff"},
            "homeScore": {},
            "awayScore": {},
            "status": {"type": "notstarted"},
            "startTimestamp": 1700000000,
        }
        result = _transform_event(raw)
        assert result["status"] == "upcoming"
        assert result["score"]["sets"] == []

    def test_completed_match(self):
        from app.services.real_tennis_service import _transform_event
        raw = {
            "id": 789,
            "tournament": {"id": 1, "name": "Wimbledon", "category": {"name": "ATP"}},
            "roundInfo": {},
            "homeTeam": {"name": "Federer"},
            "awayTeam": {"name": "Nadal"},
            "homeScore": {"period1": 6, "period2": 3, "period3": 6},
            "awayScore": {"period1": 4, "period2": 6, "period3": 4},
            "status": {"type": "finished"},
            "startTimestamp": 1700000000,
        }
        result = _transform_event(raw)
        assert result["status"] == "completed"
        assert result["score"]["sets"] == [[6, 4], [3, 6], [6, 4]]

    def test_missing_fields_handled_gracefully(self):
        from app.services.real_tennis_service import _transform_event
        raw = {"id": 999, "status": {"type": "notstarted"}}
        result = _transform_event(raw)
        assert result["player1"] == "Unknown"
        assert result["player2"] == "Unknown"
        assert result["score"]["sets"] == []
        assert result["tournament"]["name"] == ""


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
