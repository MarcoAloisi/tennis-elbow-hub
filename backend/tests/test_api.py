"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test the root endpoint returns welcome message."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Tennis Tracker" in data["message"]

    def test_health_check(self, client: TestClient) -> None:
        """Test the health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestLiveScoresEndpoints:
    """Tests for live scores API endpoints."""

    def test_get_scores_returns_list(self, client: TestClient) -> None:
        """Test that get scores returns a list structure."""
        response = client.get("/api/scores")

        assert response.status_code == 200
        data = response.json()
        assert "servers" in data
        assert "total" in data
        assert "timestamp" in data
        assert isinstance(data["servers"], list)

    def test_get_scores_with_filter(self, client: TestClient) -> None:
        """Test filtering scores by surface."""
        response = client.get("/api/scores?surface=clay")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["servers"], list)

    def test_get_scores_started_only(self, client: TestClient) -> None:
        """Test filtering for started matches only."""
        response = client.get("/api/scores?started_only=true")

        assert response.status_code == 200


class TestMatchAnalysisEndpoints:
    """Tests for match analysis API endpoints."""

    def test_sample_analysis(self, client: TestClient) -> None:
        """Test the sample analysis endpoint."""
        response = client.get("/api/analysis/sample")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stats" in data
        assert data["stats"]["info"]["player1_name"] is not None

    def test_upload_invalid_file_type(self, client: TestClient) -> None:
        """Test uploading an invalid file type."""
        # Create a fake text file
        response = client.post(
            "/api/analysis/upload",
            files={"file": ("test.txt", b"not html", "text/plain")},
        )

        assert response.status_code == 400

    def test_upload_valid_html(self, client: TestClient, sample_match_html: str) -> None:
        """Test uploading a valid HTML file."""
        response = client.post(
            "/api/analysis/upload",
            files={"file": ("match.html", sample_match_html.encode(), "text/html")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "filename" in data
