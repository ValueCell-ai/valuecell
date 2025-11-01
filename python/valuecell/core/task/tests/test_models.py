"""
Unit tests for valuecell.core.task.models module
"""

from datetime import datetime
from unittest.mock import patch


from valuecell.core.task.models import Task, TaskPattern, TaskStatus


class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.WAITING_INPUT == "waiting_input"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_task_status_members(self):
        """Test TaskStatus enum members."""
        assert len(TaskStatus) == 6
        assert TaskStatus.PENDING in TaskStatus
        assert TaskStatus.RUNNING in TaskStatus
        assert TaskStatus.WAITING_INPUT in TaskStatus
        assert TaskStatus.COMPLETED in TaskStatus
        assert TaskStatus.FAILED in TaskStatus
        assert TaskStatus.CANCELLED in TaskStatus


class TestTaskPattern:
    """Test TaskPattern enum."""

    def test_task_pattern_values(self):
        """Test TaskPattern enum values."""
        assert TaskPattern.ONCE == "once"
        assert TaskPattern.RECURRING == "recurring"

    def test_task_pattern_members(self):
        """Test TaskPattern enum members."""
        assert len(TaskPattern) == 2
        assert TaskPattern.ONCE in TaskPattern
        assert TaskPattern.RECURRING in TaskPattern


class TestTask:
    """Test Task model."""

    def test_task_creation_minimal(self):
        """Test creating a task with minimal required fields."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
        )

        assert task.task_id == "test-task-123"
        assert task.query == "Test query"
        assert task.conversation_id == "conv-123"
        assert task.user_id == "user-123"
        assert task.agent_name == "test-agent"
        assert task.status == TaskStatus.PENDING
        assert task.pattern == TaskPattern.ONCE
        assert task.remote_task_ids == []
        assert task.error_message is None
        assert task.started_at is None
        assert task.completed_at is None
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    def test_task_creation_full(self):
        """Test creating a task with all fields."""
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        updated_at = datetime(2023, 1, 1, 12, 5, 0)

        with patch("valuecell.core.task.models.datetime") as mock_datetime:
            mock_datetime.now.return_value = created_at

            task = Task(
                task_id="test-task-123",
                query="Test query",
                conversation_id="conv-123",
                user_id="user-123",
                agent_name="test-agent",
                status=TaskStatus.RUNNING,
                pattern=TaskPattern.RECURRING,
                remote_task_ids=["remote-1", "remote-2"],
                error_message="Test error",
                started_at=datetime(2023, 1, 1, 12, 1, 0),
                completed_at=datetime(2023, 1, 1, 12, 4, 0),
                updated_at=updated_at,
            )

            assert task.task_id == "test-task-123"
            assert task.status == TaskStatus.RUNNING
            assert task.pattern == TaskPattern.RECURRING
            assert task.remote_task_ids == ["remote-1", "remote-2"]
            assert task.error_message == "Test error"
            assert task.started_at == datetime(2023, 1, 1, 12, 1, 0)
            assert task.completed_at == datetime(2023, 1, 1, 12, 4, 0)
            assert task.updated_at == updated_at

    def test_start_task(self):
        """Test start_task method."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
        )

        with patch("valuecell.core.task.models.datetime") as mock_datetime:
            start_time = datetime(2023, 1, 1, 12, 1, 0)
            mock_datetime.now.return_value = start_time

            task.start()

            assert task.status == TaskStatus.RUNNING
            assert task.started_at == start_time
            assert task.updated_at == start_time

    def test_complete_task(self):
        """Test complete_task method."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )

        with patch("valuecell.core.task.models.datetime") as mock_datetime:
            complete_time = datetime(2023, 1, 1, 12, 5, 0)
            mock_datetime.now.return_value = complete_time

            task.complete()

            assert task.status == TaskStatus.COMPLETED
            assert task.completed_at == complete_time
            assert task.updated_at == complete_time

    def test_fail_task(self):
        """Test fail_task method."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )

        with patch("valuecell.core.task.models.datetime") as mock_datetime:
            fail_time = datetime(2023, 1, 1, 12, 5, 0)
            mock_datetime.now.return_value = fail_time

            task.fail("Test error message")

            assert task.status == TaskStatus.FAILED
            assert task.completed_at == fail_time
            assert task.updated_at == fail_time
            assert task.error_message == "Test error message"

    def test_cancel_task(self):
        """Test cancel_task method."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )

        with patch("valuecell.core.task.models.datetime") as mock_datetime:
            cancel_time = datetime(2023, 1, 1, 12, 5, 0)
            mock_datetime.now.return_value = cancel_time

            task.cancel()

            assert task.status == TaskStatus.CANCELLED
            assert task.completed_at == cancel_time
            assert task.updated_at == cancel_time

    def test_is_finished_completed(self):
        """Test is_finished returns True for completed task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.COMPLETED,
        )

        assert task.is_finished() is True

    def test_is_finished_failed(self):
        """Test is_finished returns True for failed task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.FAILED,
        )

        assert task.is_finished() is True

    def test_is_finished_cancelled(self):
        """Test is_finished returns True for cancelled task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.CANCELLED,
        )

        assert task.is_finished() is True

    def test_is_finished_pending(self):
        """Test is_finished returns False for pending task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.PENDING,
        )

        assert task.is_finished() is False

    def test_is_finished_running(self):
        """Test is_finished returns False for running task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )

        assert task.is_finished() is False

    def test_is_running_true(self):
        """Test is_running returns True for running task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.RUNNING,
        )

        assert task.is_running() is True

    def test_is_running_false(self):
        """Test is_running returns False for non-running task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.PENDING,
        )

        assert task.is_running() is False

    def test_is_waiting_input_true(self):
        """Test is_waiting_input returns True for waiting input task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.WAITING_INPUT,
        )

        assert task.is_waiting_input() is True

    def test_is_waiting_input_false(self):
        """Test is_waiting_input returns False for non-waiting task."""
        task = Task(
            task_id="test-task-123",
            query="Test query",
            conversation_id="conv-123",
            user_id="user-123",
            agent_name="test-agent",
            status=TaskStatus.PENDING,
        )

        assert task.is_waiting_input() is False
