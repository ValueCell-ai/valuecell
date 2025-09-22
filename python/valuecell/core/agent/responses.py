"""User-facing response constructors under valuecell.core.agent.

Prefer importing from here if you're already working inside the core.agent
namespace. For a stable top-level import, you can also use
`valuecell.responses` which provides the same API.

Example:
    from valuecell.core.agent.responses import stream, notify
    # Or explicit aliases for clarity:
    from valuecell.core.agent.responses import streaming, notification

    yield stream.message_chunk("Thinking…")
    yield stream.reasoning("Plan: 1) fetch 2) analyze")
    yield stream.tool_call_start("call_1", "search")
    yield stream.tool_call_result('{"items": 12}', "call_1", "search")
    yield stream.done()

    send(notify.message("Task submitted"))
    send(notify.done("OK"))
"""

from __future__ import annotations

from typing import Optional

from valuecell.core.types import (
    NotifyResponse,
    NotifyResponseEvent,
    StreamResponse,
    StreamResponseEvent,
    ToolCallContent,
)


class _StreamResponseNamespace:
    """Factory methods for streaming responses."""

    def message_chunk(self, content: str) -> StreamResponse:
        return StreamResponse(event=StreamResponseEvent.MESSAGE_CHUNK, content=content)

    def tool_call_started(self, tool_call_id: str, tool_name: str) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.TOOL_CALL_STARTED,
            metadata=ToolCallContent(
                tool_call_id=tool_call_id, tool_name=tool_name
            ).model_dump(),
        )

    def tool_call_completed(
        self, tool_result: str, tool_call_id: str, tool_name: str
    ) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.TOOL_CALL_COMPLETED,
            metadata=ToolCallContent(
                tool_call_id=tool_call_id, tool_name=tool_name, tool_result=tool_result
            ).model_dump(),
        )

    def reasoning(self, content: str) -> StreamResponse:
        return StreamResponse(
            event=StreamResponseEvent.REASONING,
            content=content,
        )

    def done(self, content: Optional[str] = None) -> StreamResponse:
        return StreamResponse(
            content=content,
            event=StreamResponseEvent.TASK_DONE,
        )

    def failed(self, content: Optional[str] = None) -> StreamResponse:
        return StreamResponse(
            content=content,
            event=StreamResponseEvent.TASK_FAILED,
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
            event=NotifyResponseEvent.TASK_DONE,
        )

    def failed(self, content: Optional[str] = None) -> NotifyResponse:
        return NotifyResponse(
            content=content,
            event=NotifyResponse.TASK_FAILED,
        )


notification = _NotifyResponseNamespace()


__all__ = [
    "streaming",
    "notification",
    "StreamResponse",
    "NotifyResponse",
]
