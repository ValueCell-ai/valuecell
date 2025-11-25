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
    ComponentType,
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
        self,
        user_id: str,
        conversation_id: str,
        agent_name: str,
        title: str | None = None,
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
            self.task_id = "task-1"

        def is_finished(self):
            self.calls += 1
            return self.calls >= 3

    sleeps: list[float] = []

    async def fake_sleep(duration):
        sleeps.append(duration)
        return None

    monkeypatch.setattr("valuecell.core.task.executor.asyncio.sleep", fake_sleep)

    # Ensure the TaskService.get_task returns the dummy so the executor can
    # refresh the task state during the cancellable sleep loop.
    dummy = DummyTask()
    task_service.get_task = AsyncMock(return_value=dummy)

    await executor._sleep_with_cancellation(dummy, delay=0.2)

    assert sleeps


@pytest.mark.asyncio
async def test_execute_plan_emits_end_once_when_on_before_done_used(
    monkeypatch: pytest.MonkeyPatch, task_service: TaskService
):
    """If execute_task emits END via on_before_done, execute_plan should not duplicate it in finally."""
    event_service = StubEventService()
    executor = TaskExecutor(
        agent_connections=SimpleNamespace(),
        task_service=task_service,
        event_service=event_service,
        conversation_service=StubConversationService(),
    )

    # Patch execute_task to invoke on_before_done and yield its response
    async def fake_execute_task(task, thread_id, metadata, on_before_done=None):
        if on_before_done is not None:
            maybe = await on_before_done()
            if maybe is not None:
                yield maybe
        return

    monkeypatch.setattr(executor, "execute_task", fake_execute_task)

    # Create a plan with a single subagent handoff task
    task = _make_task(handoff_from_super_agent=True)
    plan = SimpleNamespace(
        plan_id="plan",
        conversation_id="super-conv",
        user_id="user",
        guidance_message=None,
        tasks=[task],
    )

    responses = [resp async for resp in executor.execute_plan(plan, thread_id="thread")]

    # Count END-phase subagent components; should be exactly one
    import json as _json

    end_components = []
    for r in responses:
        if r.event == CommonResponseEvent.COMPONENT_GENERATOR:
            payload = _json.loads(r.data.payload.content)  # type: ignore[attr-defined]
            if payload.get("phase") == SubagentConversationPhase.END.value:
                end_components.append(r)

    assert len(end_components) == 1


@pytest.mark.asyncio
async def test_execute_task_scheduled_emits_controller_and_done(
    monkeypatch: pytest.MonkeyPatch, task_service: TaskService
):
    """_execute_task should emit controller component, await on_before_done, then done for scheduled tasks."""
    event_service = StubEventService()
    executor = TaskExecutor(
        agent_connections=SimpleNamespace(),
        task_service=task_service,
        event_service=event_service,
        conversation_service=StubConversationService(),
    )

    # Avoid real remote execution in the loop
    async def fake_single_run(task, thread_id, metadata):
        if False:
            yield  # pragma: no cover
        return

    monkeypatch.setattr(executor, "_execute_single_task_run", fake_single_run)
    # Short-circuit scheduling loop
    monkeypatch.setattr(
        "valuecell.core.task.executor.calculate_next_execution_delay",
        lambda *_args, **_kwargs: 0,
    )

    schedule = ScheduleConfig(interval_minutes=1)
    task = _make_task(schedule=schedule, pattern=TaskPattern.RECURRING)

    async def on_before_done_cb():
        # Emit a simple component via the factory to simulate END-like callback
        return event_service.factory.component_generator(
            conversation_id=task.conversation_id,
            thread_id="thread",
            task_id=task.task_id,
            content="{}",
            component_type=ComponentType.SUBAGENT_CONVERSATION.value,
        )

    emitted = [
        resp
        async for resp in executor.execute_task(
            task, thread_id="thread", metadata=None, on_before_done=on_before_done_cb
        )
    ]

    # First emission is the controller component
    assert (
        emitted[0].data.payload.component_type
        == ComponentType.SCHEDULED_TASK_CONTROLLER.value
    )  # type: ignore[attr-defined]
    # Callback emission should be present
    assert any(
        getattr(r.data.payload, "component_type", None)
        == ComponentType.SUBAGENT_CONVERSATION.value
        for r in emitted
    )
    # A TaskCompletedResponse should also be emitted later
    assert any(r.__class__.__name__ == "TaskCompletedResponse" for r in emitted)


@pytest.mark.asyncio
async def test_execute_single_task_run_emits_result_component_when_no_events(
    monkeypatch: pytest.MonkeyPatch, task_service: TaskService
):
    """For scheduled tasks with no streamed events, finalize emits a result component."""

    class FakeClient:
        async def send_message(self, *args, **kwargs):
            async def _empty():
                if False:
                    yield  # pragma: no cover
                return

            return _empty()

    class FakeConnections:
        async def get_client(self, *_args, **_kwargs):
            return FakeClient()

    event_service = StubEventService()
    executor = TaskExecutor(
        agent_connections=FakeConnections(),
        task_service=task_service,
        event_service=event_service,
        conversation_service=StubConversationService(),
    )

    schedule = ScheduleConfig(interval_minutes=5)
    task = _make_task(schedule=schedule, pattern=TaskPattern.RECURRING)

    emitted = [
        resp
        async for resp in executor._execute_single_task_run(
            task, thread_id="thread", metadata={}
        )
    ]

    # The final emitted item should be a SCHEDULED_TASK_RESULT component
    assert any(
        getattr(r.data.payload, "component_type", None)
        == ComponentType.SCHEDULED_TASK_RESULT.value
        for r in emitted
    )
