import pytest
from valuecell.core.coordinate.response import ResponseFactory
from valuecell.core.types import (
    BaseResponseDataPayload,
    CommonResponseEvent,
    ComponentGeneratorResponseDataPayload,
    ConversationItem,
    NotifyResponseEvent,
    Role,
    StreamResponseEvent,
    SystemResponseEvent,
    ToolCallPayload,
)


@pytest.fixture
def factory() -> ResponseFactory:
    return ResponseFactory()


def _mk_item(
    *,
    event: str,
    payload: str | None,
    role: str | Role = "agent",
    item_id: str = "it-1",
    conversation_id: str = "sess-1",
    thread_id: str | None = "th-1",
    task_id: str | None = "tk-1",
    agent_name: str | None = None,
) -> ConversationItem:
    return ConversationItem(
        item_id=item_id,
        role=role,  # stored as string in SQLite
        event=event,  # stored as string in SQLite
        conversation_id=conversation_id,
        thread_id=thread_id,
        task_id=task_id,
        payload=payload,
        agent_name=agent_name,
    )


def test_thread_started_with_payload(factory: ResponseFactory):
    payload = BaseResponseDataPayload(content="hello user").model_dump_json()
    item = _mk_item(
        event=SystemResponseEvent.THREAD_STARTED.value,
        payload=payload,
        role="user",
    )
    resp = factory.from_conversation_item(item)
    assert resp.event == SystemResponseEvent.THREAD_STARTED
    assert resp.data.payload is not None
    assert resp.data.payload.content == "hello user"  # type: ignore[attr-defined]


def test_message_chunk(factory: ResponseFactory):
    payload = BaseResponseDataPayload(content="chunk").model_dump_json()
    item = _mk_item(
        event=StreamResponseEvent.MESSAGE_CHUNK.value,
        payload=payload,
        agent_name="agent-x",
    )
    resp = factory.from_conversation_item(item)
    assert resp.event == StreamResponseEvent.MESSAGE_CHUNK
    assert resp.data.payload.content == "chunk"  # type: ignore[attr-defined]
    assert resp.data.agent_name == "agent-x"


def test_notify_message(factory: ResponseFactory):
    payload = BaseResponseDataPayload(content="notify").model_dump_json()
    item = _mk_item(event=NotifyResponseEvent.MESSAGE.value, payload=payload)
    resp = factory.from_conversation_item(item)
    assert resp.event == NotifyResponseEvent.MESSAGE
    assert resp.data.payload.content == "notify"  # type: ignore[attr-defined]


def test_reasoning_with_payload(factory: ResponseFactory):
    payload = BaseResponseDataPayload(content="thinking...").model_dump_json()
    item = _mk_item(event=StreamResponseEvent.REASONING.value, payload=payload)
    resp = factory.from_conversation_item(item)
    assert resp.event == StreamResponseEvent.REASONING
    assert resp.data.payload.content == "thinking..."  # type: ignore[attr-defined]


def test_component_generator(factory: ResponseFactory):
    payload = ComponentGeneratorResponseDataPayload(
        content="render this", component_type="chart"
    ).model_dump_json()
    item = _mk_item(
        event=CommonResponseEvent.COMPONENT_GENERATOR.value,
        payload=payload,
    )
    resp = factory.from_conversation_item(item)
    assert resp.event == CommonResponseEvent.COMPONENT_GENERATOR
    assert resp.data.payload.component_type == "chart"  # type: ignore[attr-defined]


def test_tool_call_completed(factory: ResponseFactory):
    payload = ToolCallPayload(
        tool_call_id="tc-1", tool_name="search", tool_result="{result}"
    ).model_dump_json()
    item = _mk_item(
        event=StreamResponseEvent.TOOL_CALL_COMPLETED.value,
        payload=payload,
    )
    resp = factory.from_conversation_item(item)
    assert resp.event == StreamResponseEvent.TOOL_CALL_COMPLETED
    assert resp.data.payload.tool_name == "search"  # type: ignore[attr-defined]
