from __future__ import annotations

import asyncio
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from app.adapters.weixin_adapter import weixin_adapter
from app.core import db
from app.core.events import event_hub


TERMINAL_STATUSES = {"success", "failed", "cancelled"}
TASK_CATEGORIES = {
    "message": {"label": "消息发送", "prefixes": ("message.",), "types": ("message.send",)},
    "file": {"label": "附件发送", "prefixes": ("file.",), "types": ("file.send",)},
    "contacts": {"label": "通讯录", "prefixes": ("contacts.",), "types": ()},
    "autoreply": {"label": "自动应答", "prefixes": ("autoreply.",), "types": ()},
    "moments": {"label": "朋友圈", "prefixes": ("moments.",), "types": ()},
    "customers": {"label": "客户资源", "prefixes": ("customers.",), "types": ()},
    "settings": {"label": "系统配置", "prefixes": ("settings.",), "types": ()},
    "other": {"label": "其他任务", "prefixes": (), "types": ()},
}
TASK_TYPE_LABELS = {
    "message.send": "发送消息",
    "file.send": "发送附件",
    "contacts.friends": "同步好友",
    "contacts.friend_detail": "同步好友详情",
    "contacts.groups": "同步群聊",
    "contacts.group_members": "同步群成员",
    "autoreply.start": "启动自动应答",
    "autoreply.stop": "停止自动应答",
    "moments.export": "朋友圈历史任务",
    "moments.post": "发布朋友圈",
    "customers.add_friends": "批量添加好友",
    "settings.wechat": "更新微信设置",
}
STATUS_ORDER = ("pending", "running", "success", "failed", "cancelled")


class TaskManager:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._worker is None or self._worker.done():
            self._queue = asyncio.Queue()
            self._running = True
            self._worker = asyncio.create_task(self._run(), name="autowechat-task-worker")

    async def stop(self) -> None:
        self._running = False
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass

    async def enqueue(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = uuid.uuid4().hex
        now = db.utc_now()
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO tasks (id, type, status, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, task_type, "pending", db.encode_json(payload), now),
            )
        await self.log(task_id, "info", f"任务已创建: {task_type}")
        if self._queue is None:
            self._queue = asyncio.Queue()
        await self._queue.put(task_id)
        return self.get(task_id)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [db.row_to_task(row) for row in rows]

    def statistics(self) -> dict[str, Any]:
        with db.connect() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        tasks = [db.row_to_task(row) for row in rows]
        total = len(tasks)
        status_counts = Counter(task["status"] for task in tasks)
        category_rows: dict[str, Counter[str]] = defaultdict(Counter)
        type_rows: dict[str, Counter[str]] = defaultdict(Counter)
        daily_rows: dict[str, Counter[str]] = defaultdict(Counter)
        durations: list[float] = []

        for task in tasks:
            task_type = task["type"]
            status = task["status"]
            category = category_for_type(task_type)
            category_rows[category][status] += 1
            type_rows[task_type][status] += 1
            created_date = str(task.get("created_at") or "")[:10] or "unknown"
            daily_rows[created_date][status] += 1
            if task.get("started_at") and task.get("finished_at"):
                duration = seconds_between(task["started_at"], task["finished_at"])
                if duration is not None:
                    durations.append(duration)

        completed = sum(status_counts[status] for status in TERMINAL_STATUSES)
        success_count = status_counts["success"]
        return {
            "summary": {
                "total": total,
                "active": status_counts["pending"] + status_counts["running"],
                "pending": status_counts["pending"],
                "running": status_counts["running"],
                "success": success_count,
                "failed": status_counts["failed"],
                "cancelled": status_counts["cancelled"],
                "success_rate": round(success_count / completed * 100) if completed else 0,
                "avg_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
            },
            "categories": [
                statistics_row(key, config["label"], category_rows[key])
                for key, config in TASK_CATEGORIES.items()
                if key != "other" or sum(category_rows[key].values())
            ],
            "types": [
                {
                    **statistics_row(task_type, TASK_TYPE_LABELS.get(task_type, task_type), counts),
                    "type": task_type,
                    "category": category_for_type(task_type),
                    "category_label": TASK_CATEGORIES[category_for_type(task_type)]["label"],
                }
                for task_type, counts in sorted(type_rows.items())
            ],
            "daily": [
                {
                    "date": date,
                    "total": sum(counts.values()),
                    **{status: counts[status] for status in STATUS_ORDER},
                }
                for date, counts in sorted(daily_rows.items(), reverse=True)[:14]
            ],
        }

    def get(self, task_id: str) -> dict[str, Any]:
        with db.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            logs = conn.execute(
                "SELECT level, message, created_at FROM task_logs WHERE task_id = ? ORDER BY id ASC",
                (task_id,),
            ).fetchall()
        if row is None:
            raise KeyError(task_id)
        task = db.row_to_task(row)
        task["logs"] = [dict(log) for log in logs]
        return task

    async def cancel(self, task_id: str) -> dict[str, Any]:
        task = self.get(task_id)
        if task["status"] == "pending":
            self._update(task_id, status="cancelled", finished_at=db.utc_now())
            await self.log(task_id, "warning", "任务已取消")
        elif task["status"] == "running":
            await self.log(task_id, "warning", "任务正在执行，无法强制中断底层微信 UI 操作")
        return self.get(task_id)

    async def log(self, task_id: str, level: str, message: str) -> None:
        event = {
            "event": "task.log",
            "task_id": task_id,
            "level": level,
            "message": message,
            "created_at": db.utc_now(),
        }
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO task_logs (task_id, level, message, created_at) VALUES (?, ?, ?, ?)",
                (task_id, level, message, event["created_at"]),
            )
        await event_hub.publish(event)

    async def _run(self) -> None:
        while self._running:
            if self._queue is None:
                self._queue = asyncio.Queue()
            task_id = await self._queue.get()
            try:
                await self._execute(task_id)
            finally:
                self._queue.task_done()

    async def _execute(self, task_id: str) -> None:
        task = self.get(task_id)
        if task["status"] == "cancelled":
            return
        self._update(task_id, status="running", started_at=db.utc_now())
        await event_hub.publish({"event": "task.updated", "task": self.get(task_id)})
        await self.log(task_id, "info", "开始执行微信自动化任务")
        try:
            result = await asyncio.to_thread(weixin_adapter.dispatch, task["type"], {**task["payload"], "_task_id": task_id})
            self._update(task_id, status="success", result=result, finished_at=db.utc_now())
            await self.log(task_id, "info", "任务执行成功")
        except Exception as exc:
            diagnostics: dict[str, Any] | None = None
            try:
                from app.services.uia_enhancer import get_uia_config, uia_enhancer

                if get_uia_config()["enabled"]:
                    diagnostics = await asyncio.to_thread(uia_enhancer.probe, save_screenshot=True)
            except Exception as diag_exc:
                await self.log(task_id, "warning", f"UIA 诊断失败: {diag_exc}")
            self._update(task_id, status="failed", error=str(exc), finished_at=db.utc_now())
            await self.log(task_id, "error", str(exc))
            if diagnostics:
                await self.log(
                    task_id,
                    "warning",
                    f"UIA 诊断: nodes={diagnostics.get('node_count')} screenshot={diagnostics.get('screenshot_path')}",
                )
        await event_hub.publish({"event": "task.updated", "task": self.get(task_id)})

    def _update(self, task_id: str, **fields: Any) -> None:
        if not fields:
            return
        normalized: dict[str, Any] = {}
        for key, value in fields.items():
            normalized[key] = db.encode_json(value) if key == "result" else value
        assignments = ", ".join(f"{key} = ?" for key in normalized)
        values = list(normalized.values()) + [task_id]
        with db.connect() as conn:
            conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", values)


task_manager = TaskManager()


def category_for_type(task_type: str) -> str:
    for key, config in TASK_CATEGORIES.items():
        if task_type in config["types"] or any(task_type.startswith(prefix) for prefix in config["prefixes"]):
            return key
    return "other"


def statistics_row(key: str, label: str, counts: Counter[str]) -> dict[str, Any]:
    total = sum(counts.values())
    completed = sum(counts[status] for status in TERMINAL_STATUSES)
    return {
        "key": key,
        "label": label,
        "total": total,
        "active": counts["pending"] + counts["running"],
        "pending": counts["pending"],
        "running": counts["running"],
        "success": counts["success"],
        "failed": counts["failed"],
        "cancelled": counts["cancelled"],
        "success_rate": round(counts["success"] / completed * 100) if completed else 0,
    }


def seconds_between(started_at: str, finished_at: str) -> float | None:
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finish = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max((finish - start).total_seconds(), 0)
