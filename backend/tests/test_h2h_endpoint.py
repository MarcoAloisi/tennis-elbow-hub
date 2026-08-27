from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_h2h_missing_params_is_422():
    response = client.get("/api/scores/h2h", params={"player_a": "Alice"})
    assert response.status_code == 422


def test_h2h_no_login_required():
    # Public endpoint — no Authorization header, must not 401.
    response = client.get(
        "/api/scores/h2h",
        params={"player_a": "___NoSuchPlayerA___", "player_b": "___NoSuchPlayerB___"},
    )
    assert response.status_code == 200


def test_h2h_response_shape_for_unknown_pair():
    response = client.get(
        "/api/scores/h2h",
        params={"player_a": "___NoSuchPlayerA___", "player_b": "___NoSuchPlayerB___"},
    )
    data = response.json()
    assert data["h2h"] == {
        "wins_a": 0,
        "wins_b": 0,
        "total": 0,
        "specific_wins_a": 0,
        "specific_wins_b": 0,
        "specific_total": 0,
    }
    assert data["form_a"] is None
    assert data["form_b"] is None
