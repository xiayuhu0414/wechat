from __future__ import annotations

from fastapi import APIRouter, Depends

from app.routers.deps import require_token
from app.schemas.models import SendMessagesRequest
from app.tasks.manager import task_manager


router = APIRouter(prefix="/api/messages", tags=["messages"], dependencies=[Depends(require_token)])


@router.post("/send")
async def send_messages(payload: SendMessagesRequest) -> dict:
    return await task_manager.enqueue("message.send", payload.model_dump())

