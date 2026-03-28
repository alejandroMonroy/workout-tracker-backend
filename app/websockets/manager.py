from typing import Any

from fastapi import WebSocket


class LiveClassManager:
    """Manages WebSocket connections per gym class schedule."""

    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, sched_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(sched_id, []).append(ws)

    def disconnect(self, sched_id: int, ws: WebSocket) -> None:
        conns = self._connections.get(sched_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, sched_id: int, data: Any) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(sched_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(sched_id, ws)


live_manager = LiveClassManager()
