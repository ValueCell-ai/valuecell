"""Task services covering task management and execution."""

from __future__ import annotations

from valuecell.core.task.manager import TaskManager
from valuecell.core.task.models import Task

DEFAULT_EXECUTION_POLL_INTERVAL = 0.1


class TaskService:
    """Expose task management independent of the orchestrator."""

    def __init__(self, manager: TaskManager | None = None) -> None:
        self._manager = manager or TaskManager()

    @property
    def manager(self) -> TaskManager:
        return self._manager

    async def update_task(self, task: Task) -> None:
        await self._manager.update_task(task)

    async def start_task(self, task_id: str) -> bool:
        return await self._manager.start_task(task_id)

    async def complete_task(self, task_id: str) -> bool:
        return await self._manager.complete_task(task_id)

    async def fail_task(self, task_id: str, reason: str) -> bool:
        return await self._manager.fail_task(task_id, reason)

    async def cancel_task(self, task_id: str) -> bool:
        return await self._manager.cancel_task(task_id)

    async def cancel_conversation_tasks(self, conversation_id: str) -> int:
        return await self._manager.cancel_conversation_tasks(conversation_id)
