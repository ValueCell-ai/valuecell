"""
Unit tests for valuecell.core.agent.responses module
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from valuecell.core.agent.responses import EventPredicates, notification, streaming
from valuecell.core.types import (
    CommonResponseEvent,
    NotifyResponseEvent,
    StreamResponseEvent,
    TaskStatusEvent,
)


class TestStreamingNamespace:
    """Test streaming response factory methods."""

    def test_message_chunk(self):
        """Test message_chunk method."""
        response = streaming.message_chunk("Hello world")

        assert response.event == StreamResponseEvent.MESSAGE_CHUNK
        assert response.content == "Hello world"
        assert response.metadata is None

    def test_tool_call_started(self):
        """Test tool_call_started method."""
        response = streaming.tool_call_started("call_123", "calculator")

        assert response.event == StreamResponseEvent.TOOL_CALL_STARTED
        assert response.content is None
        assert response.metadata is not None
        assert response.metadata["tool_call_id"] == "call_123"
        assert response.metadata["tool_name"] == "calculator"
        # tool_result is included but should be None for started events
        assert response.metadata["tool_result"] is None

    def test_tool_call_completed(self):
        """Test tool_call_completed method."""
        response = streaming.tool_call_completed("result", "call_123", "calculator")

        assert response.event == StreamResponseEvent.TOOL_CALL_COMPLETED
        assert response.content is None
        assert response.metadata is not None
        assert response.metadata["tool_call_id"] == "call_123"
        assert response.metadata["tool_name"] == "calculator"
        assert response.metadata["tool_result"] == "result"

    def test_component_generator(self):
        """Test component_generator method."""
        response = streaming.component_generator("<div/>", "widget")
        # With types updated, this should validate
        assert response.event == CommonResponseEvent.COMPONENT_GENERATOR
        assert response.content == "<div/>"
        assert response.metadata == {"component_type": "widget"}

    def test_done(self):
        """Test done method."""
        response = streaming.done("Task completed")

        assert response.event == TaskStatusEvent.TASK_COMPLETED
        assert response.content == "Task completed"

    def test_done_without_content(self):
        """Test done method without content."""
        response = streaming.done()
        assert response.event == TaskStatusEvent.TASK_COMPLETED
        assert response.content is None

    def test_failed(self):
        """Test failed method."""
        response = streaming.failed("Task failed")

        assert response.event == TaskStatusEvent.TASK_FAILED
        assert response.content == "Task failed"

    def test_failed_without_content(self):
        """Test failed method without content."""
        response = streaming.failed()

        assert response.event == TaskStatusEvent.TASK_FAILED
        assert response.content is None


class TestNotificationNamespace:
    """Test notification response factory methods."""

    def test_message(self):
        """Test message method."""
        response = notification.message("Notification message")

        assert response.event == NotifyResponseEvent.MESSAGE
        assert response.content == "Notification message"

    def test_component_generator(self):
        """Test component_generator method."""
        response = notification.component_generator("<div/>", "notice")
        assert response.event == CommonResponseEvent.COMPONENT_GENERATOR
        assert response.content == "<div/>"
        assert response.metadata == {"component_type": "notice"}

    def test_done(self):
        """Test done method."""
        response = notification.done("Notification completed")

        assert response.event == TaskStatusEvent.TASK_COMPLETED
        assert response.content == "Notification completed"

    def test_done_without_content(self):
        """Test done method without content."""
        with pytest.raises(ValidationError):
            notification.done()

    def test_failed(self):
        """Test failed method."""
        response = notification.failed("Notification failed")

        assert response.event == TaskStatusEvent.TASK_FAILED
        assert response.content == "Notification failed"

    def test_failed_without_content(self):
        """Test failed method without content."""
        with pytest.raises(ValidationError):
            notification.failed()


class TestEventPredicates:
    """Test EventPredicates class."""

    def test_is_task_completed(self):
        """Test is_task_completed predicate."""
        assert EventPredicates.is_task_completed(TaskStatusEvent.TASK_COMPLETED)
        assert not EventPredicates.is_task_completed(TaskStatusEvent.TASK_FAILED)
        assert not EventPredicates.is_task_completed(StreamResponseEvent.MESSAGE_CHUNK)

    def test_is_task_failed(self):
        """Test is_task_failed predicate."""
        assert EventPredicates.is_task_failed(TaskStatusEvent.TASK_FAILED)
        assert not EventPredicates.is_task_failed(TaskStatusEvent.TASK_COMPLETED)
        assert not EventPredicates.is_task_failed(StreamResponseEvent.MESSAGE_CHUNK)

    def test_is_tool_call(self):
        """Test is_tool_call predicate."""
        assert EventPredicates.is_tool_call(StreamResponseEvent.TOOL_CALL_STARTED)
        assert EventPredicates.is_tool_call(StreamResponseEvent.TOOL_CALL_COMPLETED)
        assert not EventPredicates.is_tool_call(StreamResponseEvent.MESSAGE_CHUNK)
        assert not EventPredicates.is_tool_call(StreamResponseEvent.REASONING)

    def test_is_reasoning(self):
        """Test is_reasoning predicate."""
        assert EventPredicates.is_reasoning(StreamResponseEvent.REASONING_STARTED)
        assert EventPredicates.is_reasoning(StreamResponseEvent.REASONING)
        assert EventPredicates.is_reasoning(StreamResponseEvent.REASONING_COMPLETED)
        assert not EventPredicates.is_reasoning(StreamResponseEvent.MESSAGE_CHUNK)
        assert not EventPredicates.is_reasoning(StreamResponseEvent.TOOL_CALL_STARTED)

    def test_is_message(self):
        """Test is_message predicate."""
        assert EventPredicates.is_message(StreamResponseEvent.MESSAGE_CHUNK)
        assert EventPredicates.is_message(NotifyResponseEvent.MESSAGE)
        assert not EventPredicates.is_message(StreamResponseEvent.TOOL_CALL_STARTED)
        assert not EventPredicates.is_message(StreamResponseEvent.REASONING)
