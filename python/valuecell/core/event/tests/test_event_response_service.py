from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from valuecell.core.event.buffer import SaveItem
from valuecell.core.event.factory import ResponseFactory
from valuecell.core.event.service import EventResponseService
from valuecell.core.types import NotifyResponseEvent, Role


class DummyBuffer:
    def __init__(self):
        self.annotated = []
        self.ingested = []
        self.flushed = []

    def annotate(self, response):
        self.annotated.append(response)
        return response

    def ingest(self, response):
        self.ingested.append(response)
        return [
            SaveItem(
                item_id="item-1",
                event=response.event,
                conversation_id=response.data.conversation_id,
                thread_id=response.data.thread_id,
                task_id=response.data.task_id,
                payload=response.data.payload,
                agent_name=response.data.agent_name,
                metadata=response.data.metadata,
                role=response.data.role,
            )
        ]

    def flush_task(self, conversation_id, thread_id, task_id):
        self.flushed.append((conversation_id, thread_id, task_id))
        return [
            SaveItem(
                item_id="item-flush",
                event=NotifyResponseEvent.MESSAGE,
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=None,
                agent_name=None,
                metadata=None,
                role=Role.AGENT,
            )
        ]


@pytest.fixture()
def response_factory() -> ResponseFactory:
    return ResponseFactory()


@pytest.fixture()
def conversation_service() -> AsyncMock:
    service = AsyncMock()
    service.add_item = AsyncMock()
    return service


@pytest.fixture()
def event_service(response_factory: ResponseFactory, conversation_service: AsyncMock):
    buffer = DummyBuffer()
    service = EventResponseService(
        conversation_service=conversation_service,
        response_factory=response_factory,
        response_buffer=buffer,
    )
    service._buffer = buffer  # type: ignore[attr-defined]
    return service


@pytest.mark.asyncio
async def test_emit_persists_items(
    event_service: EventResponseService, conversation_service: AsyncMock
):
    response = event_service.factory.message_response_general(
        event=NotifyResponseEvent.MESSAGE,
        conversation_id="conv",
        thread_id="thread",
        task_id="task",
        content="hello",
        agent_name="agent",
    )

    result = await event_service.emit(response)

    assert result is response
    conversation_service.add_item.assert_awaited_once()
    kwargs = conversation_service.add_item.call_args.kwargs
    assert kwargs["conversation_id"] == "conv"
    assert kwargs["event"] == NotifyResponseEvent.MESSAGE


@pytest.mark.asyncio
async def test_emit_many(
    event_service: EventResponseService, conversation_service: AsyncMock
):
    responses = [
        event_service.factory.message_response_general(
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv",
            thread_id="thread",
            task_id="task",
            content="one",
        ),
        event_service.factory.message_response_general(
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv",
            thread_id="thread",
            task_id="task",
            content="two",
        ),
    ]

    emitted = await event_service.emit_many(responses)

    assert emitted == responses
    assert conversation_service.add_item.await_count >= 2


@pytest.mark.asyncio
async def test_flush_task_response(
    event_service: EventResponseService, conversation_service: AsyncMock
):
    await event_service.flush_task_response("conv", "thread", "task")

    conversation_service.add_item.assert_awaited_once()
    kwargs = conversation_service.add_item.call_args.kwargs
    assert kwargs["item_id"] == "item-flush"


@pytest.mark.asyncio
async def test_route_task_status(
    monkeypatch: pytest.MonkeyPatch, event_service: EventResponseService
):
    sentinel = SimpleNamespace(done=True)

    async def fake_handle(factory, task, thread_id, event):
        return sentinel

    monkeypatch.setattr(
        "valuecell.core.event.service.handle_status_update", fake_handle
    )

    result = await event_service.route_task_status(
        task=SimpleNamespace(), thread_id="thread", event=SimpleNamespace()
    )

    assert result is sentinel
