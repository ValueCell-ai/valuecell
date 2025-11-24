from __future__ import annotations

from types import SimpleNamespace

import pytest

import valuecell.core.plan.planner as planner_mod
import valuecell.utils.model as model_utils_mod
from valuecell.core.plan.models import PlannerResponse
from valuecell.core.plan.planner import ExecutionPlanner
from valuecell.core.types import UserInput, UserInputMetadata


class StubConnections:
    def __init__(
        self,
        cards: dict[str, object] | None = None,
        planable: dict[str, object] | None = None,
    ):
        self.cards = cards or {}
        self.planable = planable or self.cards

    def get_all_agent_cards(self) -> dict[str, object]:
        return self.cards

    def get_planable_agent_cards(self) -> dict[str, object]:
        return self.planable

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
            # Provide minimal model info for error formatting paths
            self.model = SimpleNamespace(id="fake-model", provider="fake-provider")

        def run(self, *args, **kwargs):
            return paused_response

        def continue_run(self, *args, **kwargs):
            return final_response

    monkeypatch.setattr(planner_mod, "Agent", FakeAgent)
    monkeypatch.setattr(
        model_utils_mod, "get_model_for_agent", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    research_card = SimpleNamespace(name="ResearchAgent", description="Research")
    planner = ExecutionPlanner(StubConnections({"ResearchAgent": research_card}))

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
        model_utils_mod, "get_model_for_agent", lambda *args, **kwargs: "stub-model"
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


@pytest.mark.asyncio
async def test_create_plan_rejects_non_planable_agents(
    monkeypatch: pytest.MonkeyPatch,
):
    invalid_plan = PlannerResponse.model_validate(
        {
            "adequate": True,
            "reason": "ok",
            "tasks": [
                {
                    "title": "Run hidden agent",
                    "query": "Do secret things",
                    "agent_name": "HiddenAgent",
                    "pattern": "once",
                    "schedule_config": None,
                }
            ],
            "guidance_message": None,
        }
    )

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            self.model = SimpleNamespace(id="fake-model", provider="fake-provider")

        def run(self, *args, **kwargs):
            return SimpleNamespace(
                is_paused=False,
                tools_requiring_user_input=[],
                tools=[],
                content=invalid_plan,
            )

    monkeypatch.setattr(planner_mod, "Agent", FakeAgent)
    monkeypatch.setattr(
        model_utils_mod, "get_model_for_agent", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    allowed_card = SimpleNamespace(name="VisibleAgent", description="Visible")
    planner = ExecutionPlanner(
        StubConnections(
            {"VisibleAgent": allowed_card},
            planable={"VisibleAgent": allowed_card},
        )
    )

    user_input = UserInput(
        query="Use hidden agent",
        target_agent_name="VisibleAgent",
        meta=UserInputMetadata(conversation_id="conv-3", user_id="user-3"),
    )

    async def callback(_):  # pragma: no cover - should not be called
        raise AssertionError("callback should not be invoked")

    plan = await planner.create_plan(user_input, callback, "thread-77")

    assert plan.tasks == []
    assert plan.guidance_message
    assert "unsupported agent" in plan.guidance_message


def test_tool_get_enabled_agents_formats_cards(monkeypatch: pytest.MonkeyPatch):
    # Mock create_model to avoid API key validation in CI
    monkeypatch.setattr(
        model_utils_mod, "get_model_for_agent", lambda *args, **kwargs: "stub-model"
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


@pytest.mark.asyncio
async def test_create_plan_handles_malformed_response(monkeypatch: pytest.MonkeyPatch):
    """Planner returns non-PlannerResponse content -> guidance message with error."""

    malformed_content = "not-a-planner-response"

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            # Provide minimal model attributes for error formatting
            self.model = SimpleNamespace(id="fake-model", provider="fake-provider")

        def run(self, *args, **kwargs):
            return SimpleNamespace(
                is_paused=False,
                tools_requiring_user_input=[],
                tools=[],
                content=malformed_content,
            )

    monkeypatch.setattr(planner_mod, "Agent", FakeAgent)
    # Use utils module API for model stubbing per planner implementation
    monkeypatch.setattr(
        model_utils_mod, "get_model_for_agent", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    planner = ExecutionPlanner(StubConnections())
    # Ensure planner has an agent set even if __init__ path changes in future
    planner.agent = FakeAgent()

    user_input = UserInput(
        query="malformed please",
        target_agent_name="",
        meta=UserInputMetadata(conversation_id="conv-x", user_id="user-x"),
    )

    async def callback(_):
        raise AssertionError("callback should not be invoked for malformed response")

    plan = await planner.create_plan(user_input, callback, "thread-x")

    # Should return no tasks and a guidance message explaining the issue
    assert plan.tasks == []
    assert plan.guidance_message
    assert "malformed response" in plan.guidance_message
    assert malformed_content in plan.guidance_message


def test_tool_get_agent_description_dict_and_missing(monkeypatch: pytest.MonkeyPatch):
    """Cover dict formatting branch and not-found fallback in agent description."""

    class Conn(StubConnections):
        def __init__(self):
            super().__init__({"DictAgent": {"name": "DictAgent", "desc": "d"}})

    # Avoid real model creation in planner __init__
    monkeypatch.setattr(
        model_utils_mod, "get_model_for_agent", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    planner = ExecutionPlanner(Conn())

    # Dict branch returns str(dict)
    out = planner.tool_get_agent_description("DictAgent")
    assert isinstance(out, str)
    assert "DictAgent" in out

    # Not found branch
    missing = planner.tool_get_agent_description("MissingAgent")
    assert "could not be found" in missing


@pytest.mark.asyncio
async def test_lazy_init_failure_returns_guidance(monkeypatch: pytest.MonkeyPatch):
    """When planner agent cannot initialize, return guidance instead of crashing."""

    # Cause model creation to fail
    def _raise(*_args, **_kwargs):
        raise RuntimeError("no model")

    monkeypatch.setattr(model_utils_mod, "get_model_for_agent", _raise)
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    class DummyConn:
        pass

    planner = ExecutionPlanner(DummyConn())

    user_input = UserInput(
        query="plan this",
        target_agent_name="",
        meta=UserInputMetadata(conversation_id="conv-lazy", user_id="user-lazy"),
    )

    async def callback(_):
        # Should not be invoked when agent is unavailable
        raise AssertionError("callback should not be invoked")

    plan = await planner.create_plan(user_input, callback, "thread-lazy")

    assert plan.tasks == []
    assert plan.guidance_message
    assert "Planner is unavailable" in plan.guidance_message


@pytest.mark.asyncio
async def test_malformed_response_unknown_model_description(
    monkeypatch: pytest.MonkeyPatch,
):
    """Malformed planner response falls back to 'unknown model/provider' when model info missing."""

    malformed_content = "oops-not-planner-response"

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            # No model attribute to trigger unknown provider path
            pass

        def run(self, *args, **kwargs):
            return SimpleNamespace(
                is_paused=False,
                tools_requiring_user_input=[],
                tools=[],
                content=malformed_content,
            )

    monkeypatch.setattr(planner_mod, "Agent", FakeAgent)
    monkeypatch.setattr(
        model_utils_mod, "get_model_for_agent", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(planner_mod, "agent_debug_mode_enabled", lambda: False)

    planner = ExecutionPlanner(StubConnections())
    # Ensure lazy init creates our FakeAgent
    planner.agent = None

    user_input = UserInput(
        query="malformed please",
        target_agent_name="",
        meta=UserInputMetadata(conversation_id="conv-x", user_id="user-x"),
    )

    async def callback(_):
        raise AssertionError("callback should not be invoked")

    plan = await planner.create_plan(user_input, callback, "thread-x")
    assert plan.guidance_message
    assert "unknown model/provider" in plan.guidance_message
