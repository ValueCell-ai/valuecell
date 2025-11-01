import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from valuecell.core.plan.planner import UserInputRequest
from valuecell.core.plan.service import PlanService, UserInputRegistry
from valuecell.core.types import UserInput, UserInputMetadata


def test_user_input_registry_lifecycle():
    registry = UserInputRegistry()
    request = UserInputRequest(prompt="Need clarification")

    registry.add_request("conv-1", request)
    assert registry.has_request("conv-1") is True
    assert registry.get_prompt("conv-1") == "Need clarification"

    provided = registry.provide_response("conv-1", "answer")
    assert provided is True
    assert request.response == "answer"
    assert registry.has_request("conv-1") is False
    assert registry.get_prompt("conv-1") is None

    # Providing a response again should be a no-op
    assert registry.provide_response("conv-1", "ignored") is False

    registry.add_request("conv-2", request)
    registry.clear("conv-2")
    assert registry.has_request("conv-2") is False


@pytest.fixture()
def plan_service() -> PlanService:
    fake_planner = SimpleNamespace(create_plan=AsyncMock(return_value="plan"))
    return PlanService(agent_connections=Mock(), execution_planner=fake_planner)


def _make_user_input() -> UserInput:
    return UserInput(
        query="please run",
        target_agent_name="agent-x",
        meta=UserInputMetadata(conversation_id="conv", user_id="user"),
    )


def test_register_and_prompt(plan_service: PlanService):
    request = UserInputRequest(prompt="fill this")
    plan_service.register_user_input("conv", request)

    assert plan_service.has_pending_request("conv") is True
    assert plan_service.get_request_prompt("conv") == "fill this"


def test_provide_user_response(plan_service: PlanService):
    request = UserInputRequest(prompt="fill this")
    plan_service.register_user_input("conv", request)

    assert plan_service.provide_user_response("conv", "value") is True
    assert request.response == "value"
    assert plan_service.has_pending_request("conv") is False


def test_clear_pending_request(plan_service: PlanService):
    request = UserInputRequest(prompt="fill this")
    plan_service.register_user_input("conv", request)

    plan_service.clear_pending_request("conv")
    assert plan_service.has_pending_request("conv") is False


@pytest.mark.asyncio
async def test_start_planning_task_uses_asyncio_create_task(
    plan_service: PlanService, monkeypatch: pytest.MonkeyPatch
):
    scheduled_tasks: list[asyncio.Task] = []
    original_create_task = asyncio.create_task

    def fake_create_task(coro):
        task = original_create_task(coro)
        scheduled_tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    user_input = _make_user_input()
    callback = AsyncMock()

    task = plan_service.start_planning_task(user_input, "thread-1", callback)

    assert scheduled_tasks, "expected create_task to be invoked"
    await asyncio.sleep(0)
    task.cancel()
