import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from valuecell.core.coordinate.orchestrator import (
    ASYNC_SLEEP_INTERVAL,
    DEFAULT_CONTEXT_TIMEOUT_SECONDS,
    AgentOrchestrator,
    ExecutionContext,
)
from valuecell.core.event.factory import ResponseFactory
from valuecell.core.types import SystemResponseEvent


class DummyEventService:
    def __init__(self) -> None:
        self.factory = ResponseFactory()
        self.emitted: list = []

    async def emit(self, response):
        self.emitted.append(response)
        return response


class DummyPlanService:
    def __init__(self) -> None:
        self.pending = False
        self.prompt: str | None = None
        self.provided: list[tuple[str, str]] = []
        self.cleared: list[str] = []

    def has_pending_request(self, conversation_id: str) -> bool:
        return self.pending

    def get_request_prompt(self, conversation_id: str) -> str | None:
        return self.prompt

    def provide_user_response(self, conversation_id: str, response: str) -> bool:
        self.provided.append((conversation_id, response))
        return self.pending

    def register_user_input(self, conversation_id: str, request):
        pass

    def clear_pending_request(self, conversation_id: str) -> None:
        self.cleared.append(conversation_id)


class DummyConversationService:
    def __init__(self) -> None:
        self.activated: list[str] = []
        self.required: list[str] = []

    async def activate(self, conversation_id: str) -> None:
        self.activated.append(conversation_id)

    async def require_user_input(self, conversation_id: str) -> None:
        self.required.append(conversation_id)


class DummyTaskExecutor:
    def __init__(self, event_service: DummyEventService) -> None:
        self.event_service = event_service
        self.executed: list[tuple[object, str]] = []

    async def execute_plan(self, plan, thread_id: str):
        self.executed.append((plan, thread_id))
        response = self.event_service.factory.done(plan.conversation_id)
        yield await self.event_service.emit(response)


@pytest.fixture()
def orchestrator(monkeypatch: pytest.MonkeyPatch):
    event_service = DummyEventService()
    plan_service = DummyPlanService()
    conversation_service = DummyConversationService()
    task_executor = DummyTaskExecutor(event_service)

    bundle = SimpleNamespace(
        agent_connections=SimpleNamespace(),
        conversation_service=conversation_service,
        event_service=event_service,
        plan_service=plan_service,
        super_agent_service=SimpleNamespace(name="super", run=AsyncMock()),
        task_executor=task_executor,
    )

    monkeypatch.setattr(
        "valuecell.core.coordinate.orchestrator.AgentServiceBundle.compose",
        lambda **_: bundle,
    )

    orch = AgentOrchestrator()
    return orch, bundle


def test_validate_execution_context(orchestrator):
    orch, _ = orchestrator
    context = ExecutionContext(
        stage="planning", conversation_id="conv", thread_id="thread", user_id="user"
    )

    assert orch._validate_execution_context(context, "user") is True

    context.stage = ""
    assert orch._validate_execution_context(context, "user") is False

    context.stage = "planning"
    assert orch._validate_execution_context(context, "other") is False

    context.stage = "planning"
    context.created_at -= DEFAULT_CONTEXT_TIMEOUT_SECONDS + 1
    assert orch._validate_execution_context(context, "user") is False


@pytest.mark.asyncio
async def test_continue_planning_invalid_context_triggers_failure(orchestrator):
    orch, bundle = orchestrator
    loop = asyncio.get_event_loop()
    planning_future = loop.create_future()

    context = ExecutionContext(
        stage="planning", conversation_id="conv", thread_id="thread", user_id="user"
    )
    context.add_metadata(planning_task=planning_future)

    orch._execution_contexts["conv"] = context

    outputs = [
        resp async for resp in orch._continue_planning("conv", "thread", context)
    ]

    assert outputs
    assert outputs[0].event == SystemResponseEvent.PLAN_FAILED
    assert planning_future.cancelled()
    assert "conv" in bundle.plan_service.cleared
    assert "conv" in bundle.conversation_service.activated
    assert "conv" not in orch._execution_contexts


@pytest.mark.asyncio
async def test_continue_planning_pending_request_prompts_user(
    orchestrator, monkeypatch
):
    orch, bundle = orchestrator
    loop = asyncio.get_event_loop()
    planning_future = loop.create_future()

    context = ExecutionContext(
        stage="planning", conversation_id="conv", thread_id="thread", user_id="user"
    )
    context.add_metadata(planning_task=planning_future, original_user_input="query")

    bundle.plan_service.pending = True
    bundle.plan_service.prompt = "Need info"

    orch._execution_contexts["conv"] = context

    async def fast_sleep(delay):
        return None

    monkeypatch.setattr(
        "valuecell.core.coordinate.orchestrator.asyncio.sleep", fast_sleep
    )

    outputs = [
        resp async for resp in orch._continue_planning("conv", "thread", context)
    ]

    assert outputs[0].event == SystemResponseEvent.PLAN_REQUIRE_USER_INPUT
    assert "conv" in bundle.conversation_service.required
    assert "conv" in orch._execution_contexts


@pytest.mark.asyncio
async def test_continue_planning_executes_plan_when_ready(orchestrator):
    orch, bundle = orchestrator
    loop = asyncio.get_event_loop()
    planning_future = loop.create_future()
    plan = SimpleNamespace(conversation_id="conv")
    planning_future.set_result(plan)

    context = ExecutionContext(
        stage="planning", conversation_id="conv", thread_id="thread", user_id="user"
    )
    context.add_metadata(planning_task=planning_future, original_user_input="query")
    orch._execution_contexts["conv"] = context

    outputs = [
        resp async for resp in orch._continue_planning("conv", "thread", context)
    ]

    assert outputs
    assert outputs[-1].event == SystemResponseEvent.DONE
    assert "conv" not in orch._execution_contexts
    assert bundle.task_executor.executed == [(plan, "thread")]


@pytest.mark.asyncio
async def test_cleanup_expired_contexts(orchestrator):
    orch, bundle = orchestrator
    loop = asyncio.get_event_loop()
    planning_future = loop.create_future()

    context = ExecutionContext(
        stage="planning", conversation_id="conv", thread_id="thread", user_id="user"
    )
    context.add_metadata(planning_task=planning_future, original_user_input="query")
    context.created_at -= DEFAULT_CONTEXT_TIMEOUT_SECONDS + 1
    orch._execution_contexts["conv"] = context

    await orch._cleanup_expired_contexts(max_age_seconds=ASYNC_SLEEP_INTERVAL)

    assert planning_future.cancelled()
    assert "conv" in bundle.conversation_service.activated
    assert "conv" in bundle.plan_service.cleared
    assert "conv" not in orch._execution_contexts
