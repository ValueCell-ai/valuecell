from datetime import datetime
from typing import Dict

from .models import Task, TaskStatus


class TaskManager:
    """Lightweight in-memory task manager.

    Simplified to remove pluggable stores. If persistence is needed later,
    a thin adapter can wrap these methods.
    """

    def __init__(self):
        # In-memory store keyed by task_id
        self._tasks: Dict[str, Task] = {}

    # ---- basic registration ----

    async def update_task(self, task: Task) -> None:
        """Update task"""
        task.updated_at = datetime.now()
        self._tasks[task.task_id] = task

    # ---- internal helpers ----
    def _get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    # Task status management
    async def start_task(self, task_id: str) -> bool:
        """Start task execution"""
        task = self._get_task(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False

        task.start_task()
        await self.update_task(task)
        return True

    async def complete_task(self, task_id: str) -> bool:
        """Complete task"""
        task = self._get_task(task_id)
        if not task or task.is_finished():
            return False

        task.complete_task()
        await self.update_task(task)
        return True

    async def fail_task(self, task_id: str, error_message: str) -> bool:
        """Mark task as failed"""
        task = self._get_task(task_id)
        if not task or task.is_finished():
            return False

        task.fail_task(error_message)
        await self.update_task(task)
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        task = self._get_task(task_id)
        if not task or task.is_finished():
            return False

        task.cancel_task()
        await self.update_task(task)
        return True

    # Batch operations
    async def cancel_session_tasks(self, session_id: str) -> int:
        """Cancel all unfinished tasks in a session"""
        tasks = [t for t in self._tasks.values() if t.session_id == session_id]
        cancelled_count = 0

        for task in tasks:
            if not task.is_finished():
                task.cancel_task()
                await self.update_task(task)
                cancelled_count += 1

        return cancelled_count
