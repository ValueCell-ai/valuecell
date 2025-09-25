from datetime import datetime
from typing import List, Optional

from valuecell.utils import generate_uuid

from .models import Task, TaskStatus
from .store import InMemoryTaskStore, TaskStore


class TaskManager:
    """Task manager"""

    def __init__(self, store: Optional[TaskStore] = None):
        self.store = store or InMemoryTaskStore()

    async def create_task(
        self,
        session_id: str,
        user_id: str,
        agent_name: str,
    ) -> Task:
        """Create a new task"""
        task = Task(
            task_id=generate_uuid("task"),
            session_id=session_id,
            user_id=user_id,
            agent_name=agent_name,
        )
        await self.store.save_task(task)
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return await self.store.load_task(task_id)

    async def update_task(self, task: Task) -> None:
        """Update task"""
        task.updated_at = datetime.now()
        await self.store.save_task(task)

    async def delete_task(self, task_id: str) -> bool:
        """Delete task"""
        return await self.store.delete_task(task_id)

    async def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""
        return await self.store.task_exists(task_id)

    # Task status management
    async def start_task(self, task_id: str) -> bool:
        """Start task execution"""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False

        task.start_task()
        await self.update_task(task)
        return True

    async def complete_task(self, task_id: str) -> bool:
        """Complete task"""
        task = await self.get_task(task_id)
        if not task or task.is_finished():
            return False

        task.complete_task()
        await self.update_task(task)
        return True

    async def fail_task(self, task_id: str, error_message: str) -> bool:
        """Mark task as failed"""
        task = await self.get_task(task_id)
        if not task or task.is_finished():
            return False

        task.fail_task(error_message)
        await self.update_task(task)
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        task = await self.get_task(task_id)
        if not task or task.is_finished():
            return False

        task.cancel_task()
        await self.update_task(task)
        return True

    # Task queries
    async def list_tasks(
        self,
        session_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks"""
        return await self.store.list_tasks(session_id, status, limit, offset)

    async def get_session_tasks(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        """Get all tasks for a session"""
        return await self.store.get_session_tasks(session_id, limit, offset)

    async def get_tasks_by_agent(
        self, agent_name: str, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        """Get tasks by agent name"""
        return await self.store.get_tasks_by_agent(agent_name, limit, offset)

    async def get_tasks_by_user(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        """Get tasks by user ID"""
        if hasattr(self.store, "get_tasks_by_user"):
            return await self.store.get_tasks_by_user(user_id, limit, offset)

        # Fallback: filter from all tasks
        all_tasks = await self.list_tasks(limit=1000)  # Get more tasks for filtering
        user_tasks = [task for task in all_tasks if task.user_id == user_id]

        # Apply pagination manually
        start = offset
        end = offset + limit
        return user_tasks[start:end]

    async def get_running_tasks(self) -> List[Task]:
        """Get all running tasks"""
        if hasattr(self.store, "get_running_tasks"):
            return await self.store.get_running_tasks()
        return await self.list_tasks(status=TaskStatus.RUNNING)

    async def get_waiting_input_tasks(self) -> List[Task]:
        """Get all tasks waiting for user input"""
        if hasattr(self.store, "get_waiting_input_tasks"):
            return await self.store.get_waiting_input_tasks()
        return await self.list_tasks(status=TaskStatus.WAITING_INPUT)

    async def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks"""
        if hasattr(self.store, "get_pending_tasks"):
            return await self.store.get_pending_tasks()
        return await self.list_tasks(status=TaskStatus.PENDING)

    # Batch operations
    async def cancel_session_tasks(self, session_id: str) -> int:
        """Cancel all unfinished tasks in a session"""
        tasks = await self.get_session_tasks(session_id)
        cancelled_count = 0

        for task in tasks:
            if not task.is_finished():
                task.cancel_task()
                await self.update_task(task)
                cancelled_count += 1

        return cancelled_count

    async def cancel_agent_tasks(self, agent_name: str) -> int:
        """Cancel all unfinished tasks for an agent"""
        tasks = await self.get_tasks_by_agent(agent_name)
        cancelled_count = 0

        for task in tasks:
            if not task.is_finished():
                task.cancel_task()
                await self.update_task(task)
                cancelled_count += 1

        return cancelled_count
