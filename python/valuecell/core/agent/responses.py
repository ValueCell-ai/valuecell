from __future__ import annotations

from typing import Optional

from valuecell.core.types import (
    CommonResponseEvent,
    NotifyResponse,
    NotifyResponseEvent,
    StreamResponse,
    StreamResponseEvent,
    SystemResponseEvent,
    TaskStatusEvent,
    ToolCallPayload,
)


class _StreamResponseNamespace:
    """Factory methods for streaming responses."""

    def message_chunk(self, content: str) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            content=content,
        )

    def tool_call_started(self, tool_call_id: str, tool_name: str) -> StreamResponse:
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
        return StreamResponse(
            event=StreamResponseEvent.TOOL_CALL_COMPLETED,
            metadata=ToolCallPayload(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_result=tool_result,
            ).model_dump(),
        )

    def component_generator(self, content: str, component_type: str) -> StreamResponse:
        return StreamResponse(
            event=CommonResponseEvent.COMPONENT_GENERATOR,
            content=content,
            metadata={"component_type": component_type},
        )

    def done(self, content: Optional[str] = None) -> StreamResponse:
        return StreamResponse(
            content=content,
            event=TaskStatusEvent.TASK_COMPLETED,
        )

    def failed(self, content: Optional[str] = None) -> StreamResponse:
        return StreamResponse(
            content=content,
            event=SystemResponseEvent.TASK_FAILED,
        )


streaming = _StreamResponseNamespace()


class _NotifyResponseNamespace:
    """Factory methods for notify responses."""

    def message(self, content: str) -> NotifyResponse:
        return NotifyResponse(
            content=content,
            event=NotifyResponseEvent.MESSAGE,
        )

    def component_generator(self, content: str, component_type: str) -> StreamResponse:
        return StreamResponse(
            event=CommonResponseEvent.COMPONENT_GENERATOR,
            content=content,
            metadata={"component_type": component_type},
        )

    def done(self, content: Optional[str] = None) -> NotifyResponse:
        return NotifyResponse(
            content=content,
            event=TaskStatusEvent.TASK_COMPLETED,
        )

    def failed(self, content: Optional[str] = None) -> NotifyResponse:
        return NotifyResponse(
            content=content,
            event=SystemResponseEvent.TASK_FAILED,
        )


notification = _NotifyResponseNamespace()


class EventPredicates:
    """Utilities to classify response event types.

    These mirror the helper predicates previously defined in decorator.py
    and centralize them next to response event definitions.
    """

    @staticmethod
    def is_task_completed(response_type) -> bool:
        return response_type in {
            TaskStatusEvent.TASK_COMPLETED,
        }

    @staticmethod
    def is_task_failed(response_type) -> bool:
        return response_type in {
            SystemResponseEvent.TASK_FAILED,
        }

    @staticmethod
    def is_tool_call(response_type) -> bool:
        return response_type in {
            StreamResponseEvent.TOOL_CALL_STARTED,
            StreamResponseEvent.TOOL_CALL_COMPLETED,
        }

    @staticmethod
    def is_reasoning(response_type) -> bool:
        return response_type in {
            StreamResponseEvent.REASONING_STARTED,
            StreamResponseEvent.REASONING,
            StreamResponseEvent.REASONING_COMPLETED,
        }

    @staticmethod
    def is_message(response_type) -> bool:
        return response_type in {
            StreamResponseEvent.MESSAGE_CHUNK,
            NotifyResponseEvent.MESSAGE,
        }


__all__ = [
    "streaming",
    "notification",
    "EventPredicates",
]
