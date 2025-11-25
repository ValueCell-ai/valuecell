import asyncio
from datetime import datetime
from typing import Optional

from .models import Task, TaskStatus
from .task_store import InMemoryTaskStore, TaskStore


class TaskManager:
    """Lightweight task manager with pluggable storage backend.

    Defaults to in-memory storage for backward compatibility. Pass a TaskStore
    implementation (e.g., SQLiteTaskStore) for persistent storage.
    """

    def __init__(self, store: Optional[TaskStore] = None):
        # Use provided store or default to in-memory
        self._store = store or InMemoryTaskStore()
        # Process-local concurrency guard; protects in-memory state
        self._lock = asyncio.Lock()

    # ---- basic registration ----

    async def update_task(self, task: Task) -> None:
        """Update task"""
        async with self._lock:
            # Explicit updates should refresh updated_at
            task.updated_at = datetime.now()
            await self._store.save_task(task)

    # ---- internal helpers ----
    async def _get_task(self, task_id: str) -> Task | None:
        return await self._store.load_task(task_id)

    # Task status management
    async def start_task(self, task_id: str) -> bool:
        """Start task execution"""
        async with self._lock:
            task = await self._get_task(task_id)
            if not task or task.status != TaskStatus.PENDING:
                return False

            task.start()
            await self._store.save_task(task)
            return True

    async def complete_task(self, task_id: str) -> bool:
        """Complete task"""
        async with self._lock:
            task = await self._get_task(task_id)
            if not task or task.is_finished():
                return False

            task.complete()
            await self._store.save_task(task)
            return True

    async def fail_task(self, task_id: str, error_message: str) -> bool:
        """Mark task as failed"""
        async with self._lock:
            task = await self._get_task(task_id)
            if not task or task.is_finished():
                return False

            task.fail(error_message)
            await self._store.save_task(task)
            return True

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        async with self._lock:
            task = await self._get_task(task_id)
            if not task:
                return False
            if task.is_finished():
                return True

            task.cancel()
            await self._store.save_task(task)
            return True

    # Batch operations
    async def cancel_conversation_tasks(self, conversation_id: str) -> int:
        """Cancel all unfinished tasks in a conversation"""
        async with self._lock:
            tasks = await self._store.list_tasks(conversation_id=conversation_id)
            cancelled_count = 0

            for task in tasks:
                if not task.is_finished():
                    task.cancel()
                    await self._store.save_task(task)
                    cancelled_count += 1

            return cancelled_count
