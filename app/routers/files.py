from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import settings
from app.routers.deps import require_token
from app.schemas.models import SendFilesRequest
from app.tasks.manager import task_manager


router = APIRouter(prefix="/api/files", tags=["files"], dependencies=[Depends(require_token)])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
    settings.ensure_dirs()
    safe_name = Path(file.filename or "upload.bin").name
    target = settings.uploads_dir / safe_name
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return {"path": str(target), "filename": safe_name}


@router.post("/send")
async def send_files(payload: SendFilesRequest) -> dict:
    return await task_manager.enqueue("file.send", payload.model_dump())

