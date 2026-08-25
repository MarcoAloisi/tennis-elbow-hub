"""Tests for the ScraperService."""

import asyncio

import pytest

from app.services.scraper import ScraperService


class TestFetchServersFailureHandling:
    """A failed upstream fetch must not blank out the last known good data."""

    @pytest.mark.asyncio
    async def test_failed_fetch_keeps_previous_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ScraperService()

        # Seed the cache with a successful fetch.
        raw_data = '0 0 "A vs B" 0 0 0 0 "" "0-0" 0 0 0 "Clay" 1'
        monkeypatch.setattr(service, "fetch_raw_data", _async_return(raw_data))
        first = await service.fetch_servers(track_stats=False)
        assert first.total == 1

        # Simulate a transient upstream failure.
        monkeypatch.setattr(service, "fetch_raw_data", _async_return(None))
        second = await service.fetch_servers(track_stats=False)

        assert second.total == 1
        assert second is service.get_latest_data()
        assert service.get_latest_data().total == 1

    @pytest.mark.asyncio
    async def test_failed_fetch_does_not_notify_listeners(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ScraperService()
        monkeypatch.setattr(service, "fetch_raw_data", _async_return(None))

        waiter = asyncio.ensure_future(service.wait_for_update())
        await service.fetch_servers(track_stats=False)

        # A failed fetch must not wake up WebSocket listeners waiting for new data.
        done, pending = await asyncio.wait([waiter], timeout=0.05)
        assert waiter in pending
        waiter.cancel()


def _async_return(value):
    async def _inner() -> object:
        return value

    return _inner
