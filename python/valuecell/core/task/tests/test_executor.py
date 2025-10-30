import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from valuecell.core.event.factory import ResponseFactory
from valuecell.core.task.executor import ScheduledTaskResultAccumulator, TaskExecutor
from valuecell.core.task.models import ScheduleConfig, Task, TaskPattern
from valuecell.core.task.service import TaskService
from valuecell.core.types import (
    CommonResponseEvent,
    NotifyResponseEvent,
    StreamResponseEvent,
    SubagentConversationPhase,
)


class StubEventService:
    def __init__(self) -> None:
        self.factory = ResponseFactory()
        self.emitted: list = []
        self.flushed: list[tuple[str, str | None, str | None]] = []

    async def emit(self, response):
        self.emitted.append(response)
        return response

    async def flush_task_response(self, conversation_id, thread_id, task_id):
        self.flushed.append((conversation_id, thread_id, task_id))


class StubConversationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def ensure_conversation(
        self, user_id: str, conversation_id: str, agent_name: str
    ):
        self.calls.append((user_id, conversation_id))


@pytest.fixture()
def task_service() -> TaskService:
    svc = TaskService(manager=AsyncMock())
    svc.manager.start_task = AsyncMock(return_value=True)
    svc.manager.complete_task = AsyncMock(return_value=True)
    svc.manager.fail_task = AsyncMock(return_value=True)
    svc.manager.update_task = AsyncMock()
    return svc


def _make_task(schedule: ScheduleConfig | None = None, **overrides) -> Task:
    defaults = dict(
        task_id="task-1",
        title="My Task",
        query="do it",
        conversation_id="conv",
        user_id="user",
        agent_name="agent",
        schedule_config=schedule,
    )
    defaults.update(overrides)
    return Task(**defaults)


def test_accumulator_passthrough_when_disabled():
    task = _make_task(schedule=None)
    accumulator = ScheduledTaskResultAccumulator(task)
    factory = ResponseFactory()

    message = factory.message_response_general(
        event=NotifyResponseEvent.MESSAGE,
        conversation_id="conv",
        thread_id="thread",
        task_id="task",
        content="hello",
    )

    out = accumulator.consume([message])
    assert out == [message]
    assert accumulator.finalize(factory) is None


def test_accumulator_collects_and_finalizes_content():
    schedule = ScheduleConfig(interval_minutes=10)
    task = _make_task(schedule=schedule, pattern=TaskPattern.RECURRING)
    accumulator = ScheduledTaskResultAccumulator(task)
    factory = ResponseFactory()

    msg = factory.message_response_general(
        event=StreamResponseEvent.MESSAGE_CHUNK,
        conversation_id="conv",
        thread_id="thread",
        task_id="task",
        content="chunk",
    )
    reasoning = factory.reasoning(
        conversation_id="conv",
        thread_id="thread",
        task_id="task",
        event=StreamResponseEvent.REASONING,
        content="thinking",
    )
    tool = factory.tool_call(
        event=StreamResponseEvent.TOOL_CALL_STARTED,
        conversation_id="conv",
        thread_id="thread",
        task_id="task",
        tool_call_id="tc",
        tool_name="tool",
    )

    out = accumulator.consume([msg, reasoning, tool])
    assert out == []

    final_component = accumulator.finalize(factory)
    assert final_component is not None
    payload = json.loads(final_component.data.payload.content)  # type: ignore[attr-defined]
    assert payload["result"] == "chunk"
    assert "create_time" in payload
    assert final_component.data.metadata == {"task_title": "My Task"}


def test_accumulator_finalize_default_message():
    schedule = ScheduleConfig(interval_minutes=5)
    task = _make_task(schedule=schedule, pattern=TaskPattern.RECURRING)
    accumulator = ScheduledTaskResultAccumulator(task)
    factory = ResponseFactory()

    final_component = accumulator.finalize(factory)
    assert final_component is not None
    payload = json.loads(final_component.data.payload.content)  # type: ignore[attr-defined]
    assert payload["result"] == "Task completed without output."


@pytest.mark.asyncio
async def test_execute_plan_guidance_message(task_service: TaskService):
    event_service = StubEventService()
    executor = TaskExecutor(
        agent_connections=SimpleNamespace(),
        task_service=task_service,
        event_service=event_service,
        conversation_service=StubConversationService(),
    )

    plan = SimpleNamespace(
        plan_id="plan",
        conversation_id="conv",
        user_id="user",
        guidance_message="Please review",
        tasks=[],
    )

    responses = [resp async for resp in executor.execute_plan(plan, thread_id="thread")]

    assert responses[0].event == StreamResponseEvent.MESSAGE_CHUNK
    assert responses[0].data.payload.content == "Please review"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_emit_subagent_conversation_component(task_service: TaskService):
    event_service = StubEventService()
    executor = TaskExecutor(
        agent_connections=SimpleNamespace(),
        task_service=task_service,
        event_service=event_service,
        conversation_service=StubConversationService(),
    )

    task = _make_task(handoff_from_super_agent=True)
    component = await executor._emit_subagent_conversation_component(
        super_agent_conversation_id="super-conv",
        thread_id="thread",
        subagent_task=task,
        component_id="component",
        phase=SubagentConversationPhase.START,
    )

    assert component.event == CommonResponseEvent.COMPONENT_GENERATOR
    emitted_payload = json.loads(component.data.payload.content)  # type: ignore[attr-defined]
    assert emitted_payload["conversation_id"] == task.conversation_id
    assert emitted_payload["phase"] == SubagentConversationPhase.START.value
    assert component.data.item_id == "component"


@pytest.mark.asyncio
async def test_sleep_with_cancellation(
    monkeypatch: pytest.MonkeyPatch, task_service: TaskService
):
    event_service = StubEventService()
    executor = TaskExecutor(
        agent_connections=SimpleNamespace(),
        task_service=task_service,
        event_service=event_service,
        conversation_service=StubConversationService(),
        poll_interval=0.05,
    )

    class DummyTask:
        def __init__(self):
            self.calls = 0

        def is_finished(self):
            self.calls += 1
            return self.calls >= 3

    sleeps: list[float] = []

    async def fake_sleep(duration):
        sleeps.append(duration)
        return None

    monkeypatch.setattr("valuecell.core.task.executor.asyncio.sleep", fake_sleep)

    await executor._sleep_with_cancellation(DummyTask(), delay=0.2)

    assert sleeps
