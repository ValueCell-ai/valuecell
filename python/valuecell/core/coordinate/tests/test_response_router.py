"""
Unit tests for valuecell.core.coordinate.response_router module
"""

from unittest.mock import MagicMock, patch

import pytest
from a2a.types import (
    TaskState,
    TaskStatusUpdateEvent,
    TaskStatus,
    Message,
    TextPart,
    Role,
)

from valuecell.core.coordinate.response_router import (
    RouteResult,
    SideEffect,
    SideEffectKind,
    handle_status_update,
)
from valuecell.core.task import Task


class TestSideEffectKind:
    """Test SideEffectKind enum."""

    def test_enum_values(self):
        """Test SideEffectKind enum values."""
        assert SideEffectKind.FAIL_TASK.value == "fail_task"


class TestSideEffect:
    """Test SideEffect dataclass."""

    def test_init_minimal(self):
        """Test SideEffect initialization with minimal parameters."""
        effect = SideEffect(kind=SideEffectKind.FAIL_TASK)

        assert effect.kind == SideEffectKind.FAIL_TASK
        assert effect.reason is None

    def test_init_with_reason(self):
        """Test SideEffect initialization with reason."""
        effect = SideEffect(kind=SideEffectKind.FAIL_TASK, reason="Test failure")

        assert effect.kind == SideEffectKind.FAIL_TASK
        assert effect.reason == "Test failure"


class TestRouteResult:
    """Test RouteResult dataclass."""

    def test_init_minimal(self):
        """Test RouteResult initialization with minimal parameters."""
        result = RouteResult(responses=[])

        assert result.responses == []
        assert result.done is False
        assert result.side_effects == []

    def test_init_full(self):
        """Test RouteResult initialization with all parameters."""
        responses = [MagicMock()]
        side_effects = [SideEffect(kind=SideEffectKind.FAIL_TASK)]

        result = RouteResult(responses=responses, done=True, side_effects=side_effects)

        assert result.responses == responses
        assert result.done is True
        assert result.side_effects == side_effects

    def test_post_init_none_side_effects(self):
        """Test __post_init__ sets empty side_effects list when None."""
        result = RouteResult(responses=[], side_effects=None)

        assert result.side_effects == []


@pytest.mark.asyncio
class TestHandleStatusUpdate:
    """Test handle_status_update function."""

    async def test_submitted_state(self):
        """Test handling submitted task state."""
        response_factory = MagicMock()
        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.submitted),
        )

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert result.responses == []
        assert result.done is False
        assert result.side_effects == []

    async def test_completed_state(self):
        """Test handling completed task state."""
        response_factory = MagicMock()
        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.completed),
        )

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert result.responses == []
        assert result.done is False
        assert result.side_effects == []

    async def test_failed_state(self):
        """Test handling failed task state."""
        response_factory = MagicMock()
        response_factory.task_failed.return_value = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        m = Message(
            message_id="m1", role=Role.agent, parts=[TextPart(text="Task failed")]
        )
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=True,
            status=TaskStatus(state=TaskState.failed, message=m),
        )

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert len(result.responses) == 1
        assert result.done is True
        assert len(result.side_effects) == 1
        assert result.side_effects[0].kind == SideEffectKind.FAIL_TASK
        assert result.side_effects[0].reason == "Task failed"

        # Verify response_factory was called correctly
        response_factory.task_failed.assert_called_once_with(
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            content="Task failed",
        )

    async def test_failed_state_with_complex_message(self):
        """Test handling failed task state with complex message."""
        response_factory = MagicMock()
        response_factory.task_failed.return_value = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        m = Message(
            message_id="m1",
            role=Role.agent,
            parts=[TextPart(text="Complex error: something")],
        )
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=True,
            status=TaskStatus(state=TaskState.failed, message=m),
        )

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert len(result.responses) == 1
        assert result.done is True
        assert len(result.side_effects) == 1
        assert result.side_effects[0].kind == SideEffectKind.FAIL_TASK
        # Should extract text from complex message
        assert "Complex error" in result.side_effects[0].reason

    async def test_no_metadata(self):
        """Test handling event with no metadata."""
        response_factory = MagicMock()
        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.working),
        )
        # No metadata attribute

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert result.responses == []
        assert result.done is False
        assert result.side_effects == []

    async def test_tool_call_event(self):
        """Test handling tool call event."""
        response_factory = MagicMock()
        response_factory.tool_call.return_value = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        message_text = "Tool result"
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(
                state=TaskState.working,
                message=Message(
                    message_id="m1",
                    role=Role.agent,
                    parts=[TextPart(text=message_text)],
                ),
            ),
            metadata={
                "response_event": "tool_call_started",
                "tool_call_id": "call-123",
                "tool_name": "test_tool",
                "tool_result": message_text,
            },
        )

        with patch(
            "valuecell.core.agent.responses.EventPredicates.is_tool_call",
            return_value=True,
        ):
            result = await handle_status_update(
                response_factory, task, thread_id, event
            )

        assert isinstance(result, RouteResult)
        assert len(result.responses) == 1
        assert result.done is False
        assert result.side_effects == []

        # Verify response_factory was called correctly
        response_factory.tool_call.assert_called_once_with(
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            event="tool_call_started",
            tool_call_id="call-123",
            tool_name="test_tool",
            tool_result="Tool result",
        )

    async def test_tool_call_event_no_result(self):
        """Test handling tool call event without tool_result."""
        response_factory = MagicMock()
        response_factory.tool_call.return_value = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.working),
            metadata={
                "response_event": "tool_call_started",
                "tool_call_id": "call-123",
                "tool_name": "test_tool",
                # No tool_result
            },
        )

        with patch(
            "valuecell.core.agent.responses.EventPredicates.is_tool_call",
            return_value=True,
        ):
            result = await handle_status_update(
                response_factory, task, thread_id, event
            )

        assert isinstance(result, RouteResult)
        assert len(result.responses) == 1

        # Verify tool_result is None
        response_factory.tool_call.assert_called_once_with(
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            event="tool_call_started",
            tool_call_id="call-123",
            tool_name="test_tool",
            tool_result=None,
        )

    async def test_reasoning_event(self):
        """Test handling reasoning event."""
        response_factory = MagicMock()
        response_factory.reasoning.return_value = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        m = Message(
            message_id="m1", role=Role.agent, parts=[TextPart(text="Thinking...")]
        )
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.working, message=m),
            metadata={"response_event": "reasoning_started"},
        )

        with patch(
            "valuecell.core.agent.responses.EventPredicates.is_reasoning",
            return_value=True,
        ):
            result = await handle_status_update(
                response_factory, task, thread_id, event
            )

        assert isinstance(result, RouteResult)
        assert len(result.responses) == 1
        assert result.done is False
        assert result.side_effects == []

        # Verify response_factory was called correctly
        response_factory.reasoning.assert_called_once_with(
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            event="reasoning_started",
            content="Thinking...",
        )

    async def test_component_generator_event(self):
        """Test handling component generator event."""
        response_factory = MagicMock()
        response_factory.component_generator.return_value = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        m = Message(
            message_id="m1",
            role=Role.agent,
            parts=[TextPart(text="Generating component")],
        )
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.working, message=m),
            metadata={
                "response_event": "component_generator",
                "component_type": "button",
            },
        )

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert len(result.responses) == 1
        assert result.done is False
        assert result.side_effects == []

        # Verify response_factory was called correctly
        response_factory.component_generator.assert_called_once_with(
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            content="Generating component",
            component_type="button",
        )

    async def test_component_generator_event_no_component_type(self):
        """Test handling component generator event without component_type."""
        response_factory = MagicMock()
        response_factory.component_generator.return_value = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        m = Message(
            message_id="m1",
            role=Role.agent,
            parts=[TextPart(text="Generating component")],
        )
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.working, message=m),
            metadata={
                "response_event": "component_generator"
                # No component_type
            },
        )

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert len(result.responses) == 1

        # Verify component_type defaults to "unknown"
        response_factory.component_generator.assert_called_once_with(
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            content="Generating component",
            component_type="unknown",
        )

    async def test_message_event(self):
        """Test handling general message event."""
        response_factory = MagicMock()
        response_factory.message_response_general.return_value = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        m = Message(
            message_id="m1", role=Role.agent, parts=[TextPart(text="Hello world")]
        )
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.working, message=m),
            metadata={"response_event": "message"},
        )

        with patch(
            "valuecell.core.agent.responses.EventPredicates.is_message",
            return_value=True,
        ):
            result = await handle_status_update(
                response_factory, task, thread_id, event
            )

        assert isinstance(result, RouteResult)
        assert len(result.responses) == 1
        assert result.done is False
        assert result.side_effects == []

        # Verify response_factory was called correctly
        response_factory.message_response_general.assert_called_once_with(
            event="message",
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            content="Hello world",
        )

    async def test_unknown_event_type(self):
        """Test handling unknown event type."""
        response_factory = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        m = Message(
            message_id="m1", role=Role.agent, parts=[TextPart(text="Unknown event")]
        )
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.working, message=m),
            metadata={"response_event": "unknown_event"},
        )

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert result.responses == []
        assert result.done is False
        assert result.side_effects == []

    async def test_working_state_no_response_event(self):
        """Test handling working state without response_event."""
        response_factory = MagicMock()

        task = Task(
            task_id="task-123",
            conversation_id="conv-123",
            name="Test Task",
            query="Test query",
            user_id="user-123",
            agent_name="test-agent",
        )
        thread_id = "thread-123"
        m = Message(
            message_id="m1", role=Role.agent, parts=[TextPart(text="Working...")]
        )
        event = TaskStatusUpdateEvent(
            context_id="ctx-123",
            task_id="task-123",
            final=False,
            status=TaskStatus(state=TaskState.working, message=m),
            metadata={},
            # No response_event
        )

        result = await handle_status_update(response_factory, task, thread_id, event)

        assert isinstance(result, RouteResult)
        assert result.responses == []
        assert result.done is False
        assert result.side_effects == []
