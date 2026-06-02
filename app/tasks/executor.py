"""Execution is owned by TaskManager's single background worker.

This module exists as the stable import location for future executor variants
such as scheduled tasks, remote workers, or plugin runners.
"""

from app.tasks.manager import task_manager

__all__ = ["task_manager"]

