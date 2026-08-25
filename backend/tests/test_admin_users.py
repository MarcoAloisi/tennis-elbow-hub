"""Tests for the /admin/users endpoint."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.endpoints.admin import merge_auth_user_with_profile
from app.main import app

client = TestClient(app)


def test_list_users_unauthenticated():
    response = client.get("/api/admin/users")
    assert response.status_code in (401, 422)


def test_merge_admin_without_profile_is_listed():
    """Dashboard-created admins have no user_profiles row."""
    user = SimpleNamespace(
        id="admin-1",
        email="admin@example.com",
        created_at="2026-01-01T00:00:00Z",
        user_metadata={"display_name": "Boss"},
        app_metadata={"role": "admin"},
    )
    row = merge_auth_user_with_profile(user, None, online=True)
    assert row["user_id"] == "admin-1"
    assert row["email"] == "admin@example.com"
    assert row["display_name"] == "Boss"
    assert row["is_admin"] is True
    assert row["approved"] is True
    assert row["online"] is True
    assert row["in_game_name"] is None


def test_merge_regular_user_prefers_profile_fields():
    user = SimpleNamespace(
        id="u1",
        email="u@example.com",
        created_at="2026-01-01T00:00:00Z",
        user_metadata={"display_name": "FromAuth"},
        app_metadata={},
    )
    profile = SimpleNamespace(
        display_name="FromProfile",
        in_game_name="IG",
        player_name="PN",
        approved=False,
        created_at="2026-02-01T00:00:00Z",
    )
    row = merge_auth_user_with_profile(user, profile, online=False)
    assert row["display_name"] == "FromProfile"
    assert row["in_game_name"] == "IG"
    assert row["approved"] is False
    assert row["is_admin"] is False
    assert row["created_at"] == "2026-02-01T00:00:00Z"
