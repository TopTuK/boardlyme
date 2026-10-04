import uuid
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Tracks WebSocket connections per project board room."""

    def __init__(self) -> None:
        # project_id -> { websocket -> user_id }
        self._rooms: dict[uuid.UUID, dict[WebSocket, uuid.UUID]] = defaultdict(dict)

    async def connect(self, project_id: uuid.UUID, websocket: WebSocket, user_id: uuid.UUID) -> None:
        await websocket.accept()
        self._rooms[project_id][websocket] = user_id

    def disconnect(self, project_id: uuid.UUID, websocket: WebSocket) -> None:
        room = self._rooms.get(project_id)
        if room is None:
            return
        room.pop(websocket, None)
        if not room:
            self._rooms.pop(project_id, None)

    async def broadcast(self, project_id: uuid.UUID, message: dict) -> None:
        room = self._rooms.get(project_id)
        if not room:
            return
        for websocket in list(room):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(project_id, websocket)

    async def kick_user(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Force-close all sockets of a user in a room (used when membership is revoked)."""
        room = self._rooms.get(project_id)
        if room is None:
            return
        for websocket, uid in list(room.items()):
            if uid == user_id:
                try:
                    await websocket.close(code=4403)
                except Exception:
                    pass
                self.disconnect(project_id, websocket)

    async def close_room(self, project_id: uuid.UUID) -> None:
        room = self._rooms.pop(project_id, None)
        if not room:
            return
        for websocket in room:
            try:
                await websocket.close(code=4400)
            except Exception:
                pass


manager = ConnectionManager()
