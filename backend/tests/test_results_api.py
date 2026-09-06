from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_results_no_login_required():
    response = client.get("/api/scores/results")
    assert response.status_code == 200


def test_results_response_shape():
    response = client.get("/api/scores/results")
    data = response.json()
    assert set(data.keys()) == {"results", "date", "total", "page", "page_size", "total_pages"}
    assert isinstance(data["results"], list)


def test_results_unknown_player_is_empty():
    response = client.get(
        "/api/scores/results", params={"player": "___NoSuchPlayer___"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []
    assert data["total"] == 0


def test_results_invalid_mod_is_empty():
    response = client.get("/api/scores/results", params={"mod": "___not_a_mod___"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_results_bad_date_is_422():
    response = client.get("/api/scores/results", params={"date": "not-a-date"})
    assert response.status_code == 422


def test_results_page_size_over_max_is_422():
    response = client.get("/api/scores/results", params={"page_size": 500})
    assert response.status_code == 422
