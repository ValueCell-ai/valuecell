from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from valuecell.core.super_agent import core as super_agent_mod
from valuecell.core.super_agent.core import (
    SuperAgent,
    SuperAgentDecision,
    SuperAgentOutcome,
)
from valuecell.core.super_agent.service import SuperAgentService
from valuecell.core.types import UserInput, UserInputMetadata


@pytest.mark.asyncio
async def test_super_agent_run_uses_underlying_agent(monkeypatch: pytest.MonkeyPatch):
    fake_response = SimpleNamespace(
        content=SuperAgentOutcome(
            decision=SuperAgentDecision.ANSWER,
            answer_content="Here is a quick reply",
            enriched_query=None,
        )
    )

    agent_instance_holder: dict[str, object] = {}

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            self.arun = AsyncMock(return_value=fake_response)
            # Provide minimal model info for error formatting paths
            self.model = SimpleNamespace(id="fake-model", provider="fake-provider")
            agent_instance_holder["instance"] = self

    monkeypatch.setattr(super_agent_mod, "Agent", FakeAgent)
    # Patch model creation to avoid real provider/model access
    monkeypatch.setattr(
        super_agent_mod.model_utils_mod,
        "get_model_for_agent",
        lambda *args, **kwargs: "stub-model",
    )
    monkeypatch.setattr(super_agent_mod, "agent_debug_mode_enabled", lambda: False)

    sa = SuperAgent()

    user_input = UserInput(
        query="answer this",
        target_agent_name=sa.name,
        meta=UserInputMetadata(conversation_id="conv-sa", user_id="user-sa"),
    )

    result = await sa.run(user_input)

    assert result.answer_content == "Here is a quick reply"
    instance = agent_instance_holder["instance"]
    instance.arun.assert_awaited_once()
    called_args, called_kwargs = instance.arun.call_args
    assert called_args[0] == "answer this"
    assert called_kwargs["session_id"] == "conv-sa"
    assert called_kwargs["user_id"] == "user-sa"


def test_super_agent_prompts_are_non_empty():
    from valuecell.core.super_agent.prompts import (
        SUPER_AGENT_EXPECTED_OUTPUT,
        SUPER_AGENT_INSTRUCTION,
    )

    assert "<purpose>" in SUPER_AGENT_INSTRUCTION
    assert '"decision"' in SUPER_AGENT_EXPECTED_OUTPUT


@pytest.mark.asyncio
async def test_super_agent_service_delegates_to_underlying_agent():
    fake_agent = SimpleNamespace(
        name="Helper",
        run=AsyncMock(return_value="result"),
    )
    service = SuperAgentService(super_agent=fake_agent)
    user_input = UserInput(
        query="test",
        target_agent_name="Helper",
        meta=UserInputMetadata(conversation_id="conv", user_id="user"),
    )

    assert service.name == "Helper"
    outcome = await service.run(user_input)

    assert outcome == "result"
    fake_agent.run.assert_awaited_once_with(user_input)


@pytest.mark.asyncio
async def test_super_agent_run_handles_malformed_response(
    monkeypatch: pytest.MonkeyPatch,
):
    """When underlying agent returns non-SuperAgentOutcome, SuperAgent falls back to ANSWER with explanatory text."""

    # Return a malformed content (not a SuperAgentOutcome instance)
    fake_response = SimpleNamespace(content=SimpleNamespace(raw="oops"))

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            self.arun = AsyncMock(return_value=fake_response)
            # Minimal model attributes used in error formatting
            self.model = SimpleNamespace(id="fake-model", provider="fake-provider")

    monkeypatch.setattr(super_agent_mod, "Agent", FakeAgent)
    monkeypatch.setattr(
        super_agent_mod.model_utils_mod,
        "get_model_for_agent",
        lambda *args, **kwargs: "stub-model",
    )
    monkeypatch.setattr(super_agent_mod, "agent_debug_mode_enabled", lambda: False)

    sa = SuperAgent()
    user_input = UserInput(
        query="give answer",
        target_agent_name=sa.name,
        meta=UserInputMetadata(conversation_id="conv", user_id="user"),
    )

    outcome = await sa.run(user_input)

    # Fallback path should return an ANSWER decision with helpful message
    assert outcome.decision == SuperAgentDecision.ANSWER
    assert "malformed response" in outcome.answer_content
    assert "fake-model (via fake-provider)" in outcome.answer_content


@pytest.mark.asyncio
async def test_super_agent_lazy_init_failure_handoff_to_planner(
    monkeypatch: pytest.MonkeyPatch,
):
    """When SuperAgent cannot initialize, it hands off directly to Planner."""

    def _raise(*_args, **_kwargs):
        raise RuntimeError("no model")

    monkeypatch.setattr(super_agent_mod.model_utils_mod, "get_model_for_agent", _raise)
    monkeypatch.setattr(super_agent_mod, "agent_debug_mode_enabled", lambda: False)

    sa = SuperAgent()

    user_input = UserInput(
        query="please plan",
        target_agent_name=sa.name,
        meta=UserInputMetadata(conversation_id="conv-fallback", user_id="user-x"),
    )

    outcome = await sa.run(user_input)
    assert outcome.decision == SuperAgentDecision.HANDOFF_TO_PLANNER
    assert outcome.enriched_query == "please plan"
    assert outcome.reason and "missing model/provider" in outcome.reason


@pytest.mark.asyncio
async def test_super_agent_malformed_response_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
):
    """Malformed response with missing model info uses 'unknown model/provider' label."""

    # Return a malformed content (not a SuperAgentOutcome instance)
    fake_response = SimpleNamespace(content=SimpleNamespace(raw="oops"))

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            self.arun = AsyncMock(return_value=fake_response)
            # No model attribute to trigger unknown path
            # self.model = missing

    monkeypatch.setattr(super_agent_mod, "Agent", FakeAgent)
    monkeypatch.setattr(
        super_agent_mod.model_utils_mod,
        "get_model_for_agent",
        lambda *args, **kwargs: "stub-model",
    )
    monkeypatch.setattr(super_agent_mod, "agent_debug_mode_enabled", lambda: False)

    sa = SuperAgent()
    user_input = UserInput(
        query="give answer",
        target_agent_name=sa.name,
        meta=UserInputMetadata(conversation_id="conv", user_id="user"),
    )

    outcome = await sa.run(user_input)
    assert outcome.decision == SuperAgentDecision.ANSWER
    assert "unknown model/provider" in outcome.answer_content
