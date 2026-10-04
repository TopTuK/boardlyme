import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import SessionLocal
from app.models import ProjectMember
from app.security import decode_token
from app.ws import manager

router = APIRouter()


@router.websocket("/api/ws/projects/{project_id}")
async def board_socket(websocket: WebSocket, project_id: uuid.UUID) -> None:
    token = websocket.query_params.get("token") or ""
    user_id = decode_token(token, "access")
    if user_id is None:
        await websocket.accept()
        await websocket.close(code=4401)
        return

    async with SessionLocal() as db:
        member = (
            await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
                )
            )
        ).scalar_one_or_none()
    if member is None:
        await websocket.accept()
        await websocket.close(code=4403)
        return

    await manager.connect(project_id, websocket, user_id)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(project_id, websocket)
