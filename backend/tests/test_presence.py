"""Tests for PresenceManager — in-memory site-wide online tracking."""

from app.services.presence import PresenceManager


class FakeWebSocket:
    """Minimal stand-in for FastAPI's WebSocket in unit tests."""

    def __init__(self) -> None:
        self.accepted = False
        self.closed_code: int | None = None
        self.sent: list[str] = []
        self.fail_send = False

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int | None = None) -> None:
        self.closed_code = code

    async def send_text(self, message: str) -> None:
        if self.fail_send:
            raise RuntimeError("connection closed")
        self.sent.append(message)


async def test_guest_connect_is_tracked_and_counted():
    manager = PresenceManager()
    ws = FakeWebSocket()

    accepted = await manager.connect(ws, None)

    assert accepted is True
    assert ws.accepted is True
    assert manager.counts == {"registered_count": 0, "guest_count": 1}


async def test_registered_connect_dedupes_multiple_tabs():
    manager = PresenceManager()
    tab1, tab2 = FakeWebSocket(), FakeWebSocket()

    await manager.connect(tab1, "user-1")
    await manager.connect(tab2, "user-1")

    assert manager.counts == {"registered_count": 1, "guest_count": 0}
    assert manager.is_online("user-1") is True


async def test_disconnect_removes_guest():
    manager = PresenceManager()
    ws = FakeWebSocket()
    await manager.connect(ws, None)

    manager.disconnect(ws, None)

    assert manager.counts == {"registered_count": 0, "guest_count": 0}


async def test_disconnect_last_tab_marks_user_offline():
    manager = PresenceManager()
    ws = FakeWebSocket()
    await manager.connect(ws, "user-1")

    manager.disconnect(ws, "user-1")

    assert manager.is_online("user-1") is False
    assert manager.counts == {"registered_count": 0, "guest_count": 0}


async def test_disconnect_one_of_two_tabs_keeps_user_online():
    manager = PresenceManager()
    tab1, tab2 = FakeWebSocket(), FakeWebSocket()
    await manager.connect(tab1, "user-1")
    await manager.connect(tab2, "user-1")

    manager.disconnect(tab1, "user-1")

    assert manager.is_online("user-1") is True
    assert manager.counts == {"registered_count": 1, "guest_count": 0}


async def test_connect_rejects_when_at_capacity():
    manager = PresenceManager()
    manager.MAX_CONNECTIONS = 1
    first = FakeWebSocket()
    await manager.connect(first, None)

    second = FakeWebSocket()
    accepted = await manager.connect(second, None)

    assert accepted is False
    assert second.accepted is False
    assert second.closed_code == 1008


async def test_broadcast_counts_sends_to_all_and_cleans_up_failed_sockets():
    manager = PresenceManager()
    good = FakeWebSocket()
    bad = FakeWebSocket()
    bad.fail_send = True
    await manager.connect(good, None)
    await manager.connect(bad, "user-1")

    await manager.broadcast_counts()

    assert good.sent == ['{"registered_count": 1, "guest_count": 1}']
    assert manager.is_online("user-1") is False
    assert manager.counts == {"registered_count": 0, "guest_count": 1}
