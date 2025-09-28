"""
Unit tests for valuecell.core.task.manager module
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from valuecell.core.task.manager import TaskManager
from valuecell.core.task.models import Task, TaskStatus


class TestTaskManager:
    """Test TaskManager class."""

    def test_init(self):
        """Test TaskManager initialization."""
        manager = TaskManager()
        assert manager._tasks == {}

    @pytest.mark.asyncio
    async def test_update_task(self):
        """Test update_task method."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
        )

        with patch("valuecell.core.task.manager.datetime") as mock_datetime:
            update_time = datetime(2023, 1, 1, 12, 5, 0)
            mock_datetime.now.return_value = update_time

            await manager.update_task(task)

            assert task.updated_at == update_time
            assert manager._tasks["test-task-123"] == task

    def test_get_task_existing(self):
        """Test _get_task with existing task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
        )
        manager._tasks["test-task-123"] = task

        result = manager._get_task("test-task-123")
        assert result == task

    def test_get_task_nonexistent(self):
        """Test _get_task with nonexistent task."""
        manager = TaskManager()

        result = manager._get_task("nonexistent-task")
        assert result is None

    @pytest.mark.asyncio
    async def test_start_task_success(self):
        """Test start_task with valid pending task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.PENDING,
        )
        manager._tasks["test-task-123"] = task

        with (
            patch("valuecell.core.task.models.datetime") as mock_datetime,
            patch.object(manager, "update_task", new_callable=AsyncMock) as mock_update,
        ):
            start_time = datetime(2023, 1, 1, 12, 1, 0)
            mock_datetime.now.return_value = start_time

            result = await manager.start_task("test-task-123")

            assert result is True
            assert task.status == TaskStatus.RUNNING
            assert task.started_at == start_time
            assert task.updated_at == start_time
            mock_update.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_start_task_nonexistent(self):
        """Test start_task with nonexistent task."""
        manager = TaskManager()

        result = await manager.start_task("nonexistent-task")
        assert result is False

    @pytest.mark.asyncio
    async def test_start_task_already_running(self):
        """Test start_task with already running task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )
        manager._tasks["test-task-123"] = task

        result = await manager.start_task("test-task-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_complete_task_success(self):
        """Test complete_task with valid running task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )
        manager._tasks["test-task-123"] = task

        with (
            patch("valuecell.core.task.models.datetime") as mock_datetime,
            patch.object(manager, "update_task", new_callable=AsyncMock) as mock_update,
        ):
            complete_time = datetime(2023, 1, 1, 12, 5, 0)
            mock_datetime.now.return_value = complete_time

            result = await manager.complete_task("test-task-123")

            assert result is True
            assert task.status == TaskStatus.COMPLETED
            assert task.completed_at == complete_time
            assert task.updated_at == complete_time
            mock_update.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_complete_task_nonexistent(self):
        """Test complete_task with nonexistent task."""
        manager = TaskManager()

        result = await manager.complete_task("nonexistent-task")
        assert result is False

    @pytest.mark.asyncio
    async def test_complete_task_already_finished(self):
        """Test complete_task with already finished task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.COMPLETED,
        )
        manager._tasks["test-task-123"] = task

        result = await manager.complete_task("test-task-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_fail_task_success(self):
        """Test fail_task with valid running task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )
        manager._tasks["test-task-123"] = task

        with (
            patch("valuecell.core.task.models.datetime") as mock_datetime,
            patch.object(manager, "update_task", new_callable=AsyncMock) as mock_update,
        ):
            fail_time = datetime(2023, 1, 1, 12, 5, 0)
            mock_datetime.now.return_value = fail_time

            result = await manager.fail_task("test-task-123", "Test error")

            assert result is True
            assert task.status == TaskStatus.FAILED
            assert task.completed_at == fail_time
            assert task.updated_at == fail_time
            assert task.error_message == "Test error"
            mock_update.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_fail_task_nonexistent(self):
        """Test fail_task with nonexistent task."""
        manager = TaskManager()

        result = await manager.fail_task("nonexistent-task", "Test error")
        assert result is False

    @pytest.mark.asyncio
    async def test_fail_task_already_finished(self):
        """Test fail_task with already finished task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.FAILED,
        )
        manager._tasks["test-task-123"] = task

        result = await manager.fail_task("test-task-123", "Test error")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_task_success(self):
        """Test cancel_task with valid running task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )
        manager._tasks["test-task-123"] = task

        with (
            patch("valuecell.core.task.models.datetime") as mock_datetime,
            patch.object(manager, "update_task", new_callable=AsyncMock) as mock_update,
        ):
            cancel_time = datetime(2023, 1, 1, 12, 5, 0)
            mock_datetime.now.return_value = cancel_time

            result = await manager.cancel_task("test-task-123")

            assert result is True
            assert task.status == TaskStatus.CANCELLED
            assert task.completed_at == cancel_time
            assert task.updated_at == cancel_time
            mock_update.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_cancel_task_nonexistent(self):
        """Test cancel_task with nonexistent task."""
        manager = TaskManager()

        result = await manager.cancel_task("nonexistent-task")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_task_already_finished(self):
        """Test cancel_task with already finished task."""
        manager = TaskManager()
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.COMPLETED,
        )
        manager._tasks["test-task-123"] = task

        result = await manager.cancel_task("test-task-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_conversation_tasks(self):
        """Test cancel_conversation_tasks cancels all unfinished tasks in conversation."""
        manager = TaskManager()

        # Create tasks in the same conversation
        task1 = Task(
            task_id="task-1",
            query="Query 1",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )
        task2 = Task(
            task_id="task-2",
            query="Query 2",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.PENDING,
        )
        task3 = Task(
            task_id="task-3",
            query="Query 3",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.COMPLETED,  # Already finished
        )
        task4 = Task(
            task_id="task-4",
            query="Query 4",
            conversation_id="other-conv",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )

        manager._tasks = {
            "task-1": task1,
            "task-2": task2,
            "task-3": task3,
            "task-4": task4,
        }

        with (
            patch("valuecell.core.task.models.datetime") as mock_datetime,
            patch.object(manager, "update_task", new_callable=AsyncMock) as mock_update,
        ):
            cancel_time = datetime(2023, 1, 1, 12, 5, 0)
            mock_datetime.now.return_value = cancel_time

            result = await manager.cancel_conversation_tasks("conv-123")

            assert result == 2  # Two tasks were cancelled
            assert task1.status == TaskStatus.CANCELLED
            assert task1.completed_at == cancel_time
            assert task1.updated_at == cancel_time
            assert task2.status == TaskStatus.CANCELLED
            assert task2.completed_at == cancel_time
            assert task2.updated_at == cancel_time
            assert task3.status == TaskStatus.COMPLETED  # Unchanged
            assert (
                task4.status == TaskStatus.RUNNING
            )  # Different conversation, unchanged

            # update_task should be called twice
            assert mock_update.call_count == 2

    @pytest.mark.asyncio
    async def test_cancel_conversation_tasks_no_tasks(self):
        """Test cancel_conversation_tasks with no tasks in conversation."""
        manager = TaskManager()

        result = await manager.cancel_conversation_tasks("nonexistent-conv")
        assert result == 0

    @pytest.mark.asyncio
    async def test_cancel_conversation_tasks_all_finished(self):
        """Test cancel_conversation_tasks when all tasks are already finished."""
        manager = TaskManager()

        task = Task(
            task_id="task-1",
            query="Query 1",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.COMPLETED,
        )
        manager._tasks["task-1"] = task

        result = await manager.cancel_conversation_tasks("conv-123")
        assert result == 0
