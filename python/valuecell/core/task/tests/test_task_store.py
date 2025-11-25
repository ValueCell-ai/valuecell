"""
Unit tests for valuecell.core.task.task_store module
"""

import tempfile
from pathlib import Path

import pytest

from valuecell.core.task.models import Task, TaskStatus
from valuecell.core.task.task_store import InMemoryTaskStore, SQLiteTaskStore


class TestInMemoryTaskStore:
    """Test InMemoryTaskStore class."""

    @pytest.mark.asyncio
    async def test_save_and_load_task(self):
        """Test saving and loading a task."""
        store = InMemoryTaskStore()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
        )

        await store.save_task(task)
        loaded_task = await store.load_task("test-task-123")

        assert loaded_task is not None
        assert loaded_task.task_id == task.task_id
        assert loaded_task.query == task.query

    @pytest.mark.asyncio
    async def test_load_nonexistent_task(self):
        """Test loading a task that doesn't exist."""
        store = InMemoryTaskStore()
        loaded_task = await store.load_task("nonexistent")

        assert loaded_task is None

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test deleting a task."""
        store = InMemoryTaskStore()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
        )

        await store.save_task(task)
        result = await store.delete_task("test-task-123")

        assert result is True
        loaded_task = await store.load_task("test-task-123")
        assert loaded_task is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self):
        """Test deleting a task that doesn't exist."""
        store = InMemoryTaskStore()
        result = await store.delete_task("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """Test listing all tasks."""
        store = InMemoryTaskStore()
        task1 = Task(
            task_id="task-1",
            query="Query 1",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="agent-1",
        )
        task2 = Task(
            task_id="task-2",
            query="Query 2",
            conversation_id="conv-456",
            user_id="user-456",
            agent_name="agent-2",
        )

        await store.save_task(task1)
        await store.save_task(task2)

        tasks = await store.list_tasks()
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_list_tasks_by_conversation(self):
        """Test listing tasks filtered by conversation_id."""
        store = InMemoryTaskStore()
        task1 = Task(
            task_id="task-1",
            query="Query 1",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="agent-1",
        )
        task2 = Task(
            task_id="task-2",
            query="Query 2",
            conversation_id="conv-456",
            user_id="user-123",
            agent_name="agent-2",
        )

        await store.save_task(task1)
        await store.save_task(task2)

        tasks = await store.list_tasks(conversation_id="conv-123")
        assert len(tasks) == 1
        assert tasks[0].conversation_id == "conv-123"

    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self):
        """Test listing tasks filtered by status."""
        store = InMemoryTaskStore()
        task1 = Task(
            task_id="task-1",
            query="Query 1",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="agent-1",
            status=TaskStatus.RUNNING,
        )
        task2 = Task(
            task_id="task-2",
            query="Query 2",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="agent-2",
            status=TaskStatus.COMPLETED,
        )

        await store.save_task(task1)
        await store.save_task(task2)

        tasks = await store.list_tasks(status=TaskStatus.RUNNING)
        assert len(tasks) == 1
        assert tasks[0].status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_task_exists(self):
        """Test checking if a task exists."""
        store = InMemoryTaskStore()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
        )

        await store.save_task(task)

        assert await store.task_exists("test-task-123") is True
        assert await store.task_exists("nonexistent") is False


class TestSQLiteTaskStore:
    """Test SQLiteTaskStore class."""

    @pytest.mark.asyncio
    async def test_save_and_load_task(self):
        """Test saving and loading a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = SQLiteTaskStore(db_path)

            task = Task(
                task_id="test-task-123",
                query="Test query",
                conversation_id="conv-123",
                user_id="user-123",
                agent_name="test-agent",
            )

            await store.save_task(task)
            loaded_task = await store.load_task("test-task-123")

            assert loaded_task is not None
            assert loaded_task.task_id == task.task_id
            assert loaded_task.query == task.query
            assert loaded_task.conversation_id == task.conversation_id

    @pytest.mark.asyncio
    async def test_load_nonexistent_task(self):
        """Test loading a task that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = SQLiteTaskStore(db_path)

            loaded_task = await store.load_task("nonexistent")
            assert loaded_task is None

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test deleting a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = SQLiteTaskStore(db_path)

            task = Task(
                task_id="test-task-123",
                query="Test query",
                conversation_id="conv-123",
                user_id="user-123",
                agent_name="test-agent",
            )

            await store.save_task(task)
            result = await store.delete_task("test-task-123")

            assert result is True
            loaded_task = await store.load_task("test-task-123")
            assert loaded_task is None

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self):
        """Test listing tasks with various filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = SQLiteTaskStore(db_path)

            task1 = Task(
                task_id="task-1",
                query="Query 1",
                conversation_id="conv-123",
                user_id="user-123",
                agent_name="agent-1",
                status=TaskStatus.RUNNING,
            )
            task2 = Task(
                task_id="task-2",
                query="Query 2",
                conversation_id="conv-456",
                user_id="user-123",
                agent_name="agent-2",
                status=TaskStatus.COMPLETED,
            )
            task3 = Task(
                task_id="task-3",
                query="Query 3",
                conversation_id="conv-123",
                user_id="user-456",
                agent_name="agent-3",
                status=TaskStatus.RUNNING,
            )

            await store.save_task(task1)
            await store.save_task(task2)
            await store.save_task(task3)

            # Test filter by conversation_id
            tasks = await store.list_tasks(conversation_id="conv-123")
            assert len(tasks) == 2

            # Test filter by user_id
            tasks = await store.list_tasks(user_id="user-123")
            assert len(tasks) == 2

            # Test filter by status
            tasks = await store.list_tasks(status=TaskStatus.RUNNING)
            assert len(tasks) == 2

            # Test multiple filters - both task1 and task3 match conv-123 + RUNNING
            tasks = await store.list_tasks(
                conversation_id="conv-123", status=TaskStatus.RUNNING
            )
            assert len(tasks) == 2
            task_ids = {t.task_id for t in tasks}
            assert task_ids == {"task-1", "task-3"}

            # Test three filters - only task1 matches all three
            tasks = await store.list_tasks(
                conversation_id="conv-123",
                user_id="user-123",
                status=TaskStatus.RUNNING,
            )
            assert len(tasks) == 1
            assert tasks[0].task_id == "task-1"

    @pytest.mark.asyncio
    async def test_task_exists(self):
        """Test checking if a task exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = SQLiteTaskStore(db_path)

            task = Task(
                task_id="test-task-123",
                query="Test query",
                conversation_id="conv-123",
                user_id="user-123",
                agent_name="test-agent",
            )

            await store.save_task(task)

            assert await store.task_exists("test-task-123") is True
            assert await store.task_exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_persistence_across_instances(self):
        """Test that data persists across different store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")

            # Create first store instance and save task
            store1 = SQLiteTaskStore(db_path)
            task = Task(
                task_id="test-task-123",
                query="Test query",
                conversation_id="conv-123",
                user_id="user-123",
                agent_name="test-agent",
            )
            await store1.save_task(task)

            # Create second store instance and verify task exists
            store2 = SQLiteTaskStore(db_path)
            loaded_task = await store2.load_task("test-task-123")

            assert loaded_task is not None
            assert loaded_task.task_id == task.task_id
