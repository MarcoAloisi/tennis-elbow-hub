from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_player_details_unauthenticated():
    response = client.get("/api/players/Ambience", params={"elo": 2100})
    assert response.status_code in (401, 422)


def test_player_details_missing_elo_is_422():
    # Required query param — FastAPI 422 before auth.
    response = client.get("/api/players/Ambience")
    assert response.status_code == 422


def test_admin_player_detail_route_is_gone():
    response = client.get("/api/admin/players/Ambience")
    assert response.status_code == 404
