from __future__ import annotations

from fastapi import APIRouter, Depends

from app.routers.deps import require_token
from app.schemas.models import MomentsCopyRequest, MomentsPostRequest
from app.services.ai_copywriter import generate_moments_copy
from app.tasks.manager import task_manager


router = APIRouter(prefix="/api/moments", tags=["moments"], dependencies=[Depends(require_token)])


@router.post("/post")
async def post(payload: MomentsPostRequest) -> dict:
    return await task_manager.enqueue("moments.post", payload.model_dump())


@router.post("/copy")
async def copy(payload: MomentsCopyRequest) -> dict:
    return await generate_moments_copy(payload.model_dump())
