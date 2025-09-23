from __future__ import annotations

from typing import Optional

from valuecell.core.types import (
    NotifyResponse,
    NotifyResponseEvent,
    StreamResponse,
    StreamResponseEvent,
    SystemResponseEvent,
    ToolCallPayload,
    _TaskResponseEvent,
)


class _StreamResponseNamespace:
    """Factory methods for streaming responses."""

    def message_chunk(
        self, content: str, subtask_id: str | None = None
    ) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            content=content,
            subtask_id=subtask_id,
        )

    def tool_call_started(
        self, tool_call_id: str, tool_name: str, subtask_id: str | None = None
    ) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.TOOL_CALL_STARTED,
            metadata=ToolCallPayload(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
            ).model_dump(),
            subtask_id=subtask_id,
        )

    def tool_call_completed(
        self,
        tool_result: str,
        tool_call_id: str,
        tool_name: str,
        subtask_id: str | None = None,
    ) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.TOOL_CALL_COMPLETED,
            metadata=ToolCallPayload(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_result=tool_result,
            ).model_dump(),
            subtask_id=subtask_id,
        )

    def reasoning_started(self, subtask_id: str | None = None) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.REASONING_STARTED,
            subtask_id=subtask_id,
        )

    def reasoning(self, content: str, subtask_id: str | None = None) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.REASONING,
            content=content,
            subtask_id=subtask_id,
        )

    def reasoning_completed(self, subtask_id: str | None = None) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.REASONING_COMPLETED,
            subtask_id=subtask_id,
        )

    def component_generator(
        self, content: str, component_type: str, subtask_id: str | None = None
    ) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.COMPONENT_GENERATOR,
            content=content,
            metadata={"component_type": component_type},
            subtask_id=subtask_id,
        )

    def done(self, content: Optional[str] = None) -> StreamResponse:
        return StreamResponse(
            content=content,
            event=_TaskResponseEvent.TASK_COMPLETED,
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

    def done(self, content: Optional[str] = None) -> NotifyResponse:
        return NotifyResponse(
            content=content,
            event=_TaskResponseEvent.TASK_COMPLETED,
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
            _TaskResponseEvent.TASK_COMPLETED,
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


__all__ = [
    "streaming",
    "notification",
    "EventPredicates",
]
