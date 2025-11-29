import json

import pytest

from valuecell.core.event.factory import (
    ResponseFactory,
    _format_tool_result_for_frontend,
)
from valuecell.core.task.models import Task
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


def test_from_conversation_item_rejects_unknown_event(factory: ResponseFactory):
    item = ConversationItem.model_construct(
        item_id="it-1",
        role=Role.AGENT,
        agent_name=None,
        event="unknown_event",
        conversation_id="sess-1",
        thread_id="th-1",
        task_id="tk-1",
        payload="{}",
        metadata="{}",
    )
    with pytest.raises(ValueError):
        factory.from_conversation_item(item)


def test_schedule_task_controller_component(factory: ResponseFactory):
    task = Task(
        task_id="task-123",
        title="Morning report",
        query="run",
        conversation_id="conv",
        user_id="user",
        agent_name="agent",
    )

    resp = factory.schedule_task_controller_component("conv", "thread", task)

    assert resp.data.agent_name == "agent"
    assert resp.data.metadata == {"task_title": "Morning report"}
    payload = json.loads(resp.data.payload.content)  # type: ignore[attr-defined]
    assert payload["task_id"] == "task-123"


def test_schedule_task_result_component(factory: ResponseFactory):
    task = Task(
        task_id="task-456",
        title="Daily summary",
        query="run",
        conversation_id="conv",
        user_id="user",
        agent_name="agent",
    )

    resp = factory.schedule_task_result_component(task, content='{"result":1}')

    assert resp.data.agent_name == "agent"
    assert resp.data.metadata == {"task_title": "Daily summary"}
    assert resp.data.payload.content == '{"result":1}'  # type: ignore[attr-defined]


# ============================================================
# Tests for _format_tool_result_for_frontend
# ============================================================


class TestFormatToolResultForFrontend:
    """Tests for the _format_tool_result_for_frontend helper function."""

    def test_none_returns_none(self):
        assert _format_tool_result_for_frontend(None) is None

    def test_empty_string_returns_empty(self):
        assert _format_tool_result_for_frontend("") == ""

    def test_plain_string_wrapped_in_json_array(self):
        result = _format_tool_result_for_frontend("SUCCESS")
        parsed = json.loads(result)
        assert parsed == [{"content": "SUCCESS"}]

    def test_already_formatted_unchanged(self):
        already_formatted = '[{"content": "some result"}]'
        result = _format_tool_result_for_frontend(already_formatted)
        assert result == already_formatted

    def test_already_formatted_multiple_items_unchanged(self):
        already_formatted = '[{"content": "item1"}, {"content": "item2"}]'
        result = _format_tool_result_for_frontend(already_formatted)
        assert result == already_formatted

    def test_json_object_without_content_wrapped(self):
        # JSON object without 'content' key should be wrapped
        input_str = '{"key": "value"}'
        result = _format_tool_result_for_frontend(input_str)
        parsed = json.loads(result)
        assert parsed == [{"content": '{"key": "value"}'}]

    def test_json_array_without_content_wrapped(self):
        # JSON array without 'content' in first element should be wrapped
        input_str = '[{"other": "field"}]'
        result = _format_tool_result_for_frontend(input_str)
        parsed = json.loads(result)
        assert parsed == [{"content": '[{"other": "field"}]'}]

    def test_error_message_wrapped(self):
        result = _format_tool_result_for_frontend("ERROR: connection failed")
        parsed = json.loads(result)
        assert parsed == [{"content": "ERROR: connection failed"}]


# ============================================================
# Tests for tool_call method with formatting
# ============================================================


class TestToolCallMethodFormatting:
    """Tests for ResponseFactory.tool_call with tool_result formatting."""

    def test_tool_call_started_no_formatting(self, factory: ResponseFactory):
        resp = factory.tool_call(
            conversation_id="conv-1",
            thread_id="th-1",
            task_id="tk-1",
            event=StreamResponseEvent.TOOL_CALL_STARTED,
            tool_call_id="tc-1",
            tool_name="search",
            tool_result=None,
        )
        assert resp.event == StreamResponseEvent.TOOL_CALL_STARTED
        assert resp.data.payload.tool_result is None  # type: ignore[attr-defined]

    def test_tool_call_completed_formats_plain_string(self, factory: ResponseFactory):
        resp = factory.tool_call(
            conversation_id="conv-1",
            thread_id="th-1",
            task_id="tk-1",
            event=StreamResponseEvent.TOOL_CALL_COMPLETED,
            tool_call_id="tc-1",
            tool_name="search",
            tool_result="Success",
        )
        assert resp.event == StreamResponseEvent.TOOL_CALL_COMPLETED
        result = resp.data.payload.tool_result  # type: ignore[attr-defined]
        parsed = json.loads(result)
        assert parsed == [{"content": "Success"}]

    def test_tool_call_completed_preserves_already_formatted(
        self, factory: ResponseFactory
    ):
        already_formatted = '[{"content": "formatted result"}]'
        resp = factory.tool_call(
            conversation_id="conv-1",
            thread_id="th-1",
            task_id="tk-1",
            event=StreamResponseEvent.TOOL_CALL_COMPLETED,
            tool_call_id="tc-1",
            tool_name="search",
            tool_result=already_formatted,
        )
        assert resp.event == StreamResponseEvent.TOOL_CALL_COMPLETED
        assert resp.data.payload.tool_result == already_formatted  # type: ignore[attr-defined]

    def test_tool_call_completed_with_none_result(self, factory: ResponseFactory):
        resp = factory.tool_call(
            conversation_id="conv-1",
            thread_id="th-1",
            task_id="tk-1",
            event=StreamResponseEvent.TOOL_CALL_COMPLETED,
            tool_call_id="tc-1",
            tool_name="search",
            tool_result=None,
        )
        assert resp.event == StreamResponseEvent.TOOL_CALL_COMPLETED
        assert resp.data.payload.tool_result is None  # type: ignore[attr-defined]
