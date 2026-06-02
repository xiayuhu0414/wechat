from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core import db
from app.routers.deps import require_token
from app.schemas.models import AutoreplyRuleRequest, AutoreplyStartRequest, AutoreplyStopRequest
from app.tasks.manager import task_manager


router = APIRouter(prefix="/api/autoreply", tags=["autoreply"], dependencies=[Depends(require_token)])


@router.get("/rules")
def list_rules() -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM autoreply_rules ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


@router.post("/rules")
def create_rule(payload: AutoreplyRuleRequest) -> dict:
    rule_id = uuid.uuid4().hex
    now = db.utc_now()
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO autoreply_rules
            (id, name, target, target_type, keyword, reply, at_only, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule_id,
                payload.name,
                payload.target,
                payload.target_type,
                payload.keyword,
                payload.reply,
                int(payload.at_only),
                int(payload.enabled),
                now,
                now,
            ),
        )
    return {"id": rule_id, **payload.model_dump()}


@router.post("/start")
async def start(payload: AutoreplyStartRequest) -> dict:
    rules = payload.rules
    if not rules:
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM autoreply_rules WHERE target = ? AND enabled = 1",
                (payload.target,),
            ).fetchall()
        rules = [dict(row) for row in rows]
    return await task_manager.enqueue(
        "autoreply.start",
        {
            "target": payload.target,
            "duration": payload.duration,
            "rules": rules,
            "at_only": payload.at_only,
        },
    )


@router.post("/stop")
async def stop(payload: AutoreplyStopRequest) -> dict:
    return await task_manager.cancel(payload.task_id)

