"""Response service consolidating factory, buffering, and persistence."""

from __future__ import annotations

from typing import Iterable

from valuecell.core.conversation.service import ConversationService
from valuecell.core.event.buffer import ResponseBuffer, SaveItem
from valuecell.core.event.factory import ResponseFactory
from valuecell.core.event.router import RouteResult, handle_status_update
from valuecell.core.task.models import Task
from valuecell.core.types import BaseResponse


class EventResponseService:
    """Provide a single entry point for response creation and persistence."""

    def __init__(
        self,
        conversation_service: ConversationService,
        response_factory: ResponseFactory | None = None,
        response_buffer: ResponseBuffer | None = None,
    ) -> None:
        self._conversation_service = conversation_service
        self._factory = response_factory or ResponseFactory()
        self._buffer = response_buffer or ResponseBuffer()

    @property
    def factory(self) -> ResponseFactory:
        return self._factory

    @property
    def conversation_service(self) -> ConversationService:
        return self._conversation_service

    async def emit(self, response: BaseResponse) -> BaseResponse:
        """Annotate, persist, and return the response."""

        annotated = self._buffer.annotate(response)
        await self._persist_from_buffer(annotated)
        return annotated

    async def emit_many(self, responses: Iterable[BaseResponse]) -> list[BaseResponse]:
        """Persist a batch of responses in order."""

        out: list[BaseResponse] = []
        for resp in responses:
            out.append(await self.emit(resp))
        return out

    async def flush_task_response(
        self, conversation_id: str, thread_id: str | None, task_id: str | None
    ) -> None:
        """Force-flush buffered paragraphs for a task context."""

        items = self._buffer.flush_task(conversation_id, thread_id, task_id)
        await self._persist_items(items)

    async def route_task_status(self, task: Task, thread_id: str, event) -> RouteResult:
        """Route a task status update without side-effects."""

        return await handle_status_update(self._factory, task, thread_id, event)

    async def _persist_from_buffer(self, response: BaseResponse) -> None:
        items = self._buffer.ingest(response)
        await self._persist_items(items)

    async def _persist_items(self, items: list[SaveItem]) -> None:
        for item in items:
            await self._conversation_service.add_item(
                role=item.role,
                event=item.event,
                conversation_id=item.conversation_id,
                thread_id=item.thread_id,
                task_id=item.task_id,
                payload=item.payload,
                item_id=item.item_id,
                agent_name=item.agent_name,
                metadata=item.metadata,
            )
