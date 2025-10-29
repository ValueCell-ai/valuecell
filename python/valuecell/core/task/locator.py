"""Process-local TaskService singleton with override hooks.

This module provides a simple, synchronous locator for obtaining the default
TaskService instance. It supports:

- Lazy initialization (no IO on import)
- Test overrides via set_task_service
- Cleanup via reset_task_service

Note: This is a per-process singleton. For multi-process deployments, the
TaskService/TaskManager must rely on shared storage to coordinate state.
"""

from __future__ import annotations

import threading
from typing import Optional

from .manager import TaskManager
from .service import TaskService

_task_service: Optional[TaskService] = None
_lock = threading.Lock()


def get_task_service() -> TaskService:
    """Get (or create) the process-local TaskService instance."""
    global _task_service
    if _task_service is None:
        with _lock:
            if _task_service is None:
                _task_service = TaskService(manager=TaskManager())
    return _task_service


def set_task_service(service: TaskService) -> None:
    """Override the default TaskService (tests or custom wiring)."""
    global _task_service
    with _lock:
        _task_service = service


def reset_task_service() -> None:
    """Reset the singleton to an uninitialized state (tests)."""
    global _task_service
    with _lock:
        _task_service = None
