from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.events import event_hub
from app.routers.deps import require_token
from app.tasks.manager import task_manager


router = APIRouter(prefix="/api/tasks", tags=["tasks"], dependencies=[Depends(require_token)])
ws_router = APIRouter(tags=["task-events"])


@router.get("")
def list_tasks(limit: int = 100) -> list[dict]:
    return task_manager.list(limit)


@router.get("/stats")
def task_statistics() -> dict:
    return task_manager.statistics()


@router.get("/{task_id}")
def get_task(task_id: str) -> dict:
    try:
        return task_manager.get(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict:
    try:
        return await task_manager.cancel(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@ws_router.websocket("/ws/tasks/logs")
async def task_logs(websocket: WebSocket) -> None:
    if settings.api_token and websocket.query_params.get("token") != settings.api_token:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    queue = await event_hub.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        event_hub.unsubscribe(queue)
