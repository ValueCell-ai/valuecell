"""Task services covering task management and execution."""

from __future__ import annotations

from typing import List, Optional

from valuecell.core.task.manager import TaskManager
from valuecell.core.task.models import Task, TaskStatus
from valuecell.core.task.task_store import TaskStore

DEFAULT_EXECUTION_POLL_INTERVAL = 0.1


class TaskService:
    """Expose task management independent of the orchestrator."""

    def __init__(
        self, manager: TaskManager | None = None, store: TaskStore | None = None
    ) -> None:
        # If a store is provided but no manager, create manager with the store
        if manager is None and store is not None:
            self._manager = TaskManager(store=store)
        else:
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

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return await self._manager._get_task(task_id)

    async def list_tasks(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks with optional filters."""
        return await self._manager._store.list_tasks(
            conversation_id=conversation_id,
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )
