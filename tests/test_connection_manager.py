from backend.app.connection_manager import ConnectionManager

PAYLOAD = {"id": 1, "status": "inprogress", "home_score": 1, "away_score": 0, "current_minute": 23}


class FakeSocket:
    """Stands in for a WebSocket: records what it was sent, or fails on send."""

    def __init__(self, fails: bool = False):
        self.fails = fails
        self.accepted = False
        self.sent: list[dict] = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload: dict):
        if self.fails:
            raise RuntimeError("client went away")
        self.sent.append(payload)


async def test_connect_accepts_and_registers():
    manager = ConnectionManager()
    socket = FakeSocket()

    await manager.connect("a", socket)

    assert socket.accepted
    assert manager.active_connections == {"a": socket}


async def test_broadcast_reaches_every_connection():
    manager = ConnectionManager()
    first, second = FakeSocket(), FakeSocket()
    await manager.connect("a", first)
    await manager.connect("b", second)

    await manager.broadcast(PAYLOAD)

    assert first.sent == [PAYLOAD]
    assert second.sent == [PAYLOAD]


async def test_failed_connection_is_dropped_and_others_still_receive():
    manager = ConnectionManager()
    healthy, dead = FakeSocket(), FakeSocket(fails=True)
    await manager.connect("dead", dead)
    await manager.connect("healthy", healthy)

    await manager.broadcast(PAYLOAD)

    assert healthy.sent == [PAYLOAD]
    assert "dead" not in manager.active_connections
    assert "healthy" in manager.active_connections


async def test_disconnect_unknown_id_is_harmless():
    manager = ConnectionManager()

    manager.disconnect("never-connected")

    assert manager.active_connections == {}
