from __future__ import annotations

from typing import Optional

from valuecell.core.types import (
    CommonResponseEvent,
    NotifyResponse,
    NotifyResponseEvent,
    StreamResponse,
    StreamResponseEvent,
    TaskStatusEvent,
    ToolCallPayload,
)


class _StreamResponseNamespace:
    """Factory methods for streaming responses.

    Provides convenient methods to create StreamResponse instances for
    different types of streaming events like message chunks, tool calls, etc.
    """

    def message_chunk(self, content: str) -> StreamResponse:
        """Create a message chunk response.

        Args:
            content: The message content chunk

        Returns:
            StreamResponse with MESSAGE_CHUNK event
        """
        return StreamResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            content=content,
        )

    def tool_call_started(self, tool_call_id: str, tool_name: str) -> StreamResponse:
        """Create a tool call started response.

        Args:
            tool_call_id: Unique identifier for the tool call
            tool_name: Name of the tool being called

        Returns:
            StreamResponse with TOOL_CALL_STARTED event
        """
        return StreamResponse(
            event=StreamResponseEvent.TOOL_CALL_STARTED,
            metadata=ToolCallPayload(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
            ).model_dump(),
        )

    def tool_call_completed(
        self,
        tool_result: str,
        tool_call_id: str,
        tool_name: str,
    ) -> StreamResponse:
        """Create a tool call completed response.

        Args:
            tool_result: The result of the tool execution
            tool_call_id: Unique identifier for the tool call
            tool_name: Name of the tool that was called

        Returns:
            StreamResponse with TOOL_CALL_COMPLETED event
        """
        return StreamResponse(
            event=StreamResponseEvent.TOOL_CALL_COMPLETED,
            metadata=ToolCallPayload(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_result=tool_result,
            ).model_dump(),
        )

    def component_generator(
        self, content: str, component_type: str, component_id: Optional[str] = None
    ) -> StreamResponse:
        """Create a component generator response.

        Args:
            content: The component content
            component_type: Type of the component being generated
            component_id: Optional stable component ID for replace behavior.
                         If provided, this will override the auto-generated item_id,
                         allowing the frontend to replace components with the same ID.

        Returns:
            StreamResponse with COMPONENT_GENERATOR event.

        Note:
            This factory returns a `StreamResponse` (not a `NotifyResponse`) so
            the same component generator payload can be streamed and handled by
            the existing streaming pipeline. This is intentional.
        """
        metadata = {"component_type": component_type}
        if component_id is not None:
            metadata["component_id"] = component_id

        return StreamResponse(
            event=CommonResponseEvent.COMPONENT_GENERATOR,
            content=content,
            metadata=metadata,
        )

    def done(self, content: Optional[str] = None) -> StreamResponse:
        """Create a task completed response.

        Args:
            content: Optional completion message

        Returns:
            StreamResponse with TASK_COMPLETED event
        """
        return StreamResponse(
            content=content,
            event=TaskStatusEvent.TASK_COMPLETED,
        )

    def failed(self, content: Optional[str] = None) -> StreamResponse:
        """Create a task failed response.

        Args:
            content: Optional error message

        Returns:
            StreamResponse with TASK_FAILED event
        """
        return StreamResponse(
            content=content,
            event=TaskStatusEvent.TASK_FAILED,
        )


streaming = _StreamResponseNamespace()


class _NotifyResponseNamespace:
    """Factory methods for notify responses.

    Provides convenient methods to create NotifyResponse instances for
    different types of notification events.
    """

    def message(self, content: str) -> NotifyResponse:
        """Create a notification message response.

        Args:
            content: The notification content

        Returns:
            NotifyResponse with MESSAGE event
        """
        return NotifyResponse(
            content=content,
            event=NotifyResponseEvent.MESSAGE,
        )

    def component_generator(
        self, content: str, component_type: str, component_id: Optional[str] = None
    ) -> StreamResponse:
        """Create a component generator response for notifications.

        Args:
            content: The component content
            component_type: Type of the component being generated
            component_id: Optional stable component ID for replace behavior.
                         If provided, this will override the auto-generated item_id,
                         allowing the frontend to replace components with the same ID.

        Returns:
            StreamResponse with COMPONENT_GENERATOR event
        """
        metadata = {"component_type": component_type}
        if component_id is not None:
            metadata["component_id"] = component_id

        return StreamResponse(
            event=CommonResponseEvent.COMPONENT_GENERATOR,
            content=content,
            metadata=metadata,
        )

    def done(self, content: Optional[str] = None) -> NotifyResponse:
        """Create a task completed notification response.

        Args:
            content: Optional completion message

        Returns:
            NotifyResponse with TASK_COMPLETED event
        """
        return NotifyResponse(
            content=content,
            event=TaskStatusEvent.TASK_COMPLETED,
        )

    def failed(self, content: Optional[str] = None) -> NotifyResponse:
        """Create a task failed notification response.

        Args:
            content: Optional error message

        Returns:
            NotifyResponse with TASK_FAILED event
        """
        return NotifyResponse(
            content=content,
            event=TaskStatusEvent.TASK_FAILED,
        )


notification = _NotifyResponseNamespace()


class EventPredicates:
    """Utilities to classify response event types.

    These mirror the helper predicates previously defined in decorator.py
    and centralize them next to response event definitions.
    """

    @staticmethod
    def is_task_completed(response_type) -> bool:
        """Check if the response type indicates task completion.

        Args:
            response_type: The response event type to check

        Returns:
            True if the event indicates task completion
        """
        return response_type in {
            TaskStatusEvent.TASK_COMPLETED,
        }

    @staticmethod
    def is_task_failed(response_type) -> bool:
        """Check if the response type indicates task failure.

        Args:
            response_type: The response event type to check

        Returns:
            True if the event indicates task failure
        """
        return response_type in {
            TaskStatusEvent.TASK_FAILED,
        }

    @staticmethod
    def is_tool_call(response_type) -> bool:
        """Check if the response type indicates a tool call event.

        Args:
            response_type: The response event type to check

        Returns:
            True if the event is related to tool calls
        """
        return response_type in {
            StreamResponseEvent.TOOL_CALL_STARTED,
            StreamResponseEvent.TOOL_CALL_COMPLETED,
        }

    @staticmethod
    def is_reasoning(response_type) -> bool:
        """Check if the response type indicates a reasoning event.

        Args:
            response_type: The response event type to check

        Returns:
            True if the event is related to reasoning
        """
        return response_type in {
            StreamResponseEvent.REASONING_STARTED,
            StreamResponseEvent.REASONING,
            StreamResponseEvent.REASONING_COMPLETED,
        }

    @staticmethod
    def is_message(response_type) -> bool:
        """Check if the response type indicates a message event.

        Args:
            response_type: The response event type to check

        Returns:
            True if the event is a message-related event
        """
        return response_type in {
            StreamResponseEvent.MESSAGE_CHUNK,
            NotifyResponseEvent.MESSAGE,
        }


__all__ = [
    "streaming",
    "notification",
    "EventPredicates",
]
