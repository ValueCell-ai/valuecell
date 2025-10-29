from __future__ import annotations

from types import SimpleNamespace

import pytest

import valuecell.core.plan.planner as planner_mod
import valuecell.utils.model as model_utils_mod
from valuecell.core.plan.models import PlannerResponse
from valuecell.core.plan.planner import ExecutionPlanner
from valuecell.core.types import UserInput, UserInputMetadata


class StubConnections:
    def __init__(self, cards: dict[str, object] | None = None):
        self.cards = cards or {}

    def get_all_agent_cards(self) -> dict[str, object]:
        return self.cards

    def get_agent_card(self, name: str):
        return self.cards.get(name)


@pytest.mark.asyncio
async def test_create_plan_handles_paused_run(monkeypatch: pytest.MonkeyPatch):
    field = SimpleNamespace(description="Provide ticker", value=None)
    tool = SimpleNamespace(user_input_schema=[field])

    final_plan = PlannerResponse.model_validate(
        {
            "adequate": True,
            "reason": "ok",
            "tasks": [
                {
                    "title": "Research task",
                    "query": "Run research",
                    "agent_name": "ResearchAgent",
                    "pattern": "once",
                    "schedule_config": None,
                }
            ],
            "guidance_message": None,
        }
    )

    paused_response = SimpleNamespace(
        is_paused=True,
        tools_requiring_user_input=[tool],
        tools=[tool],
        content=None,
    )
    final_response = SimpleNamespace(
        is_paused=False,
        tools=[],
        tools_requiring_user_input=[],
        content=final_plan,
    )

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, *args, **kwargs):
            return paused_response

        def continue_run(self, *args, **kwargs):
            return final_response

    monkeypatch.setattr(planner_mod, "Agent", FakeAgent)
    monkeypatch.setattr(
        model_utils_mod, "create_model", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    planner = ExecutionPlanner(StubConnections())

    user_input = UserInput(
        query="Need super-agent handoff",
        target_agent_name="",
        meta=UserInputMetadata(conversation_id="conv-1", user_id="user-1"),
    )

    prompts: list[str] = []

    async def callback(request):
        prompts.append(request.prompt)
        request.provide_response("user response")

    plan = await planner.create_plan(user_input, callback, "thread-9")

    assert prompts == ["Provide ticker"]
    task = plan.tasks[0]
    assert task.handoff_from_super_agent is True
    assert task.conversation_id != "conv-1"
    assert field.value == "user response"


@pytest.mark.asyncio
async def test_create_plan_raises_on_inadequate_plan(monkeypatch: pytest.MonkeyPatch):
    inadequate_plan = PlannerResponse.model_validate(
        {
            "adequate": False,
            "reason": "need more info",
            "tasks": [],
        }
    )

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, *args, **kwargs):
            return SimpleNamespace(
                is_paused=False,
                tools_requiring_user_input=[],
                tools=[],
                content=inadequate_plan,
            )

    monkeypatch.setattr(planner_mod, "Agent", FakeAgent)
    monkeypatch.setattr(
        model_utils_mod, "create_model", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    planner = ExecutionPlanner(StubConnections())

    user_input = UserInput(
        query="Need super-agent handoff",
        target_agent_name="AgentX",
        meta=UserInputMetadata(conversation_id="conv-2", user_id="user-2"),
    )

    async def callback(request):
        raise AssertionError("callback should not be invoked")

    plan = await planner.create_plan(user_input, callback, "thread-55")
    assert plan.guidance_message


def test_tool_get_enabled_agents_formats_cards(monkeypatch: pytest.MonkeyPatch):
    # Mock create_model to avoid API key validation in CI
    monkeypatch.setattr(
        model_utils_mod, "create_model", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    skill = SimpleNamespace(
        name="Lookup",
        id="lookup",
        description="Look things up",
        examples=["Find revenue"],
        tags=["finance"],
    )
    card_alpha = SimpleNamespace(
        name="AgentAlpha",
        description="Alpha agent",
        skills=[skill],
    )
    planner = ExecutionPlanner(StubConnections({"AgentAlpha": card_alpha}))

    output = planner.tool_get_enabled_agents()

    assert "<AgentAlpha>" in output
    assert "Lookup" in output
    assert "</AgentAlpha>" in output
