import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db
from app.main import app
from app.models.match_game_event import MatchGameEvent


def _event(
    match_id: str, set_number: int, game_number: int, **overrides
) -> MatchGameEvent:
    fields = {
        "p1_games": 1,
        "p2_games": 0,
        "winner": 1,
        "server": 1,
        "is_tiebreak": False,
        "points": None,
    }
    return MatchGameEvent(
        match_id=match_id,
        set_number=set_number,
        game_number=game_number,
        **{**fields, **overrides},
    )


@pytest.fixture
async def async_client(sqlite_session_factory):
    async def _override_get_db():
        async with sqlite_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


async def test_games_are_returned_in_set_and_game_order(
    async_client, sqlite_session_factory
):
    async with sqlite_session_factory() as session:
        session.add_all(
            [
                _event("m1", 2, 1, p1_games=0, p2_games=1, winner=2, server=2),
                _event("m1", 1, 1, points=["0-0", "15-0"]),
                _event("other", 1, 1),
            ]
        )
        await session.commit()

    response = await async_client.get("/api/scores/m1/games")

    assert response.status_code == 200
    assert response.json() == [
        {
            "set_number": 1,
            "game_number": 1,
            "p1_games": 1,
            "p2_games": 0,
            "winner": 1,
            "server": 1,
            "is_tiebreak": False,
            "points": ["0-0", "15-0"],
        },
        {
            "set_number": 2,
            "game_number": 1,
            "p1_games": 0,
            "p2_games": 1,
            "winner": 2,
            "server": 2,
            "is_tiebreak": False,
            "points": None,
        },
    ]


async def test_unknown_match_returns_empty_list(async_client):
    response = await async_client.get("/api/scores/nope/games")

    assert response.status_code == 200
    assert response.json() == []
