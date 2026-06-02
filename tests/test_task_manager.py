from __future__ import annotations

import asyncio

import pytest

from app.core import db
from app.tasks.manager import TaskManager


@pytest.mark.asyncio
async def test_task_manager_runs_tasks_serially(monkeypatch, tmp_path):
    monkeypatch.setattr(db.settings, "database_path", tmp_path / "app.db")
    db.init_db()

    calls = []

    def fake_dispatch(task_type, payload):
        calls.append(task_type)
        return {"ok": True, "payload": payload}

    monkeypatch.setattr("app.tasks.manager.weixin_adapter.dispatch", fake_dispatch)

    manager = TaskManager()
    await manager.start()
    first = await manager.enqueue("message.send", {"targets": ["a"], "messages": ["1"]})
    second = await manager.enqueue("file.send", {"targets": ["b"], "files": ["x"]})
    await asyncio.wait_for(manager._queue.join(), timeout=3)
    await manager.stop()

    assert calls == ["message.send", "file.send"]
    assert manager.get(first["id"])["status"] == "success"
    assert manager.get(second["id"])["status"] == "success"

