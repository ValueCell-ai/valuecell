import asyncio
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import aiosqlite

from .models import Task, TaskStatus


class TaskStore(ABC):
    """Task storage abstract base class.

    Implementations should provide async methods to save, load, delete and
    list tasks.
    """

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
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks with optional filters."""

    @abstractmethod
    async def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""


class InMemoryTaskStore(TaskStore):
    """In-memory TaskStore implementation used for testing and simple scenarios.

    Stores tasks in a dict keyed by task_id.
    """

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
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())

        # Apply filters
        if conversation_id is not None:
            tasks = [t for t in tasks if t.conversation_id == conversation_id]
        if user_id is not None:
            tasks = [t for t in tasks if t.user_id == user_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]

        # Sort by creation time descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # Apply pagination
        start = offset
        end = offset + limit
        return tasks[start:end]

    async def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""
        return task_id in self._tasks

    def clear_all(self) -> None:
        """Clear all tasks (for testing)"""
        self._tasks.clear()

    def get_task_count(self) -> int:
        """Get total task count (for debugging)"""
        return len(self._tasks)


class SQLiteTaskStore(TaskStore):
    """SQLite-backed task store using aiosqlite for true async I/O.

    Lazily initializes the database schema on first use. Uses aiosqlite to
    perform non-blocking DB operations and converts rows to Task instances.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False
        self._init_lock = None  # lazy to avoid loop-binding in __init__

    async def _ensure_initialized(self):
        """Ensure database is initialized with proper schema."""
        if self._initialized:
            return

        if self._init_lock is None:
            self._init_lock = asyncio.Lock()

        async with self._init_lock:
            if self._initialized:
                return

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        title TEXT,
                        query TEXT NOT NULL,
                        conversation_id TEXT NOT NULL,
                        thread_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        agent_name TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        pattern TEXT NOT NULL DEFAULT 'once',
                        schedule_config TEXT,
                        handoff_from_super_agent INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        updated_at TEXT NOT NULL,
                        error_message TEXT
                    )
                    """
                )
                # Create indexes for common queries
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_conversation ON tasks(conversation_id)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
                )
                await db.commit()

            self._initialized = True

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        import json

        # Parse JSON fields
        schedule_config = None
        if row["schedule_config"]:
            try:
                schedule_config = json.loads(row["schedule_config"])
            except Exception:
                pass

        return Task(
            task_id=row["task_id"],
            title=row["title"] or "",
            query=row["query"],
            conversation_id=row["conversation_id"],
            thread_id=row["thread_id"],
            user_id=row["user_id"],
            agent_name=row["agent_name"],
            status=row["status"],
            pattern=row["pattern"],
            schedule_config=schedule_config,
            handoff_from_super_agent=bool(row["handoff_from_super_agent"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"])
            if row["started_at"]
            else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
            updated_at=datetime.fromisoformat(row["updated_at"]),
            error_message=row["error_message"],
        )

    async def save_task(self, task: Task) -> None:
        """Save task to SQLite database."""
        import json

        await self._ensure_initialized()

        # Serialize complex fields
        schedule_config_json = None
        if task.schedule_config:
            schedule_config_json = json.dumps(task.schedule_config.model_dump())

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO tasks (
                    task_id, title, query, conversation_id, thread_id, user_id, agent_name,
                    status, pattern, schedule_config, handoff_from_super_agent,
                    created_at, started_at, completed_at, updated_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.title,
                    task.query,
                    task.conversation_id,
                    task.thread_id,
                    task.user_id,
                    task.agent_name,
                    task.status.value
                    if hasattr(task.status, "value")
                    else str(task.status),
                    task.pattern.value
                    if hasattr(task.pattern, "value")
                    else str(task.pattern),
                    schedule_config_json,
                    int(task.handoff_from_super_agent),
                    task.created_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.updated_at.isoformat(),
                    task.error_message,
                ),
            )
            await db.commit()

    async def load_task(self, task_id: str) -> Optional[Task]:
        """Load task from SQLite database."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            )
            row = await cur.fetchone()
            return self._row_to_task(row) if row else None

    async def delete_task(self, task_id: str) -> bool:
        """Delete task from SQLite database."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "DELETE FROM tasks WHERE task_id = ?",
                (task_id,),
            )
            await db.commit()
            return cur.rowcount > 0

    async def list_tasks(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks from SQLite database with optional filters."""
        await self._ensure_initialized()

        # Build query with filters
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if conversation_id is not None:
            query += " AND conversation_id = ?"
            params.append(conversation_id)

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status.value if hasattr(status, "value") else str(status))

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(query, params)
            rows = await cur.fetchall()
            return [self._row_to_task(row) for row in rows]

    async def task_exists(self, task_id: str) -> bool:
        """Check if task exists in SQLite database."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT 1 FROM tasks WHERE task_id = ?",
                (task_id,),
            )
            row = await cur.fetchone()
            return row is not None
