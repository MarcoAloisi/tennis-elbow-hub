from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_my_profile_unauthenticated():
    response = client.get("/api/profile/me")
    assert response.status_code in (401, 422)  # missing auth header

def test_update_profile_unauthenticated():
    response = client.put("/api/profile/me", json={"display_name": "New Name"})
    assert response.status_code in (401, 422)

def test_get_public_profile_unauthenticated():
    response = client.get("/api/profile/some-user-id")
    assert response.status_code in (401, 422)
