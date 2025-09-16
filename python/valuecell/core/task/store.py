from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .models import Task, TaskStatus


class TaskStore(ABC):
    """Task storage abstract base class"""

    @abstractmethod
    async def save_task(self, task: Task) -> None:
        """Save task"""

    @abstractmethod
    async def load_task(self, task_id: str) -> Optional[Task]:
        """Load task"""

    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """Delete task"""

    @abstractmethod
    async def list_tasks(
        self,
        session_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks"""

    @abstractmethod
    async def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""

    @abstractmethod
    async def get_tasks_by_agent(
        self, agent_name: str, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        """Get tasks by agent name"""

    @abstractmethod
    async def get_session_tasks(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        """Get all tasks for a session"""


class InMemoryTaskStore(TaskStore):
    """In-memory task storage implementation"""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    async def save_task(self, task: Task) -> None:
        """Save task to memory"""
        self._tasks[task.task_id] = task

    async def load_task(self, task_id: str) -> Optional[Task]:
        """Load task from memory"""
        return self._tasks.get(task_id)

    async def delete_task(self, task_id: str) -> bool:
        """Delete task from memory"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    async def list_tasks(
        self,
        session_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks"""
        tasks = list(self._tasks.values())

        # Apply filters
        if session_id is not None:
            tasks = [task for task in tasks if task.session_id == session_id]

        if status is not None:
            tasks = [task for task in tasks if task.status == status]

        # Sort by creation time descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # Apply pagination
        start = offset
        end = offset + limit
        return tasks[start:end]

    async def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""
        return task_id in self._tasks

    async def get_tasks_by_agent(
        self, agent_name: str, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        """Get tasks by agent name"""
        agent_tasks = [
            task for task in self._tasks.values() if task.agent_name == agent_name
        ]

        # Sort by creation time descending
        agent_tasks.sort(key=lambda t: t.created_at, reverse=True)

        # Apply pagination
        start = offset
        end = offset + limit
        return agent_tasks[start:end]

    async def get_session_tasks(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[Task]:
        """Get all tasks for a session"""
        session_tasks = [
            task for task in self._tasks.values() if task.session_id == session_id
        ]

        # Sort by creation time ascending (session tasks in chronological order)
        session_tasks.sort(key=lambda t: t.created_at)

        # Apply pagination
        start = offset
        end = offset + limit
        return session_tasks[start:end]

    async def get_running_tasks(self) -> List[Task]:
        """Get all running tasks"""
        return [
            task for task in self._tasks.values() if task.status == TaskStatus.RUNNING
        ]

    async def get_waiting_input_tasks(self) -> List[Task]:
        """Get all tasks waiting for user input"""
        return [
            task
            for task in self._tasks.values()
            if task.status == TaskStatus.WAITING_INPUT
        ]

    async def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks"""
        return [
            task for task in self._tasks.values() if task.status == TaskStatus.PENDING
        ]

    def clear_all(self) -> None:
        """Clear all tasks (for testing)"""
        self._tasks.clear()

    def get_task_count(self) -> int:
        """Get total task count (for debugging)"""
        return len(self._tasks)

    def get_task_count_by_status(self, status: TaskStatus) -> int:
        """Get task count by status (for debugging)"""
        return len([task for task in self._tasks.values() if task.status == status])
