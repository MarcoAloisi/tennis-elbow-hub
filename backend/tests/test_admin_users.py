"""Tests for the /admin/users endpoint.

Only the unauthenticated path is tested here — this repo has no test-DB
isolation (see plan's Global Constraints), and the endpoint's happy path
queries the live user_profiles table, so it isn't safe to exercise with a
bypassed auth dependency in an automated test. The online-flag computation
itself (presence_manager.is_online) is covered by test_presence.py.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_users_unauthenticated():
    response = client.get("/api/admin/users")
    assert response.status_code in (401, 422)
