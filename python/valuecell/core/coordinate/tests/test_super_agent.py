from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from valuecell.core.coordinate import super_agent as super_agent_mod
from valuecell.core.coordinate.super_agent import SuperAgent, SuperAgentDecision
from valuecell.core.types import UserInput, UserInputMetadata


@pytest.mark.asyncio
async def test_super_agent_run_uses_underlying_agent(monkeypatch: pytest.MonkeyPatch):
    fake_response = SimpleNamespace(
        content=SimpleNamespace(
            decision=SuperAgentDecision.ANSWER,
            answer_content="Here is a quick reply",
            enriched_query=None,
        )
    )

    agent_instance_holder: dict[str, object] = {}

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            self.arun = AsyncMock(return_value=fake_response)
            agent_instance_holder["instance"] = self

    monkeypatch.setattr(super_agent_mod, "Agent", FakeAgent)
    monkeypatch.setattr(super_agent_mod, "get_model", lambda _: "stub-model")
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
    from valuecell.core.coordinate.super_agent_prompts import (
        SUPER_AGENT_EXPECTED_OUTPUT,
        SUPER_AGENT_INSTRUCTION,
    )

    assert "<purpose>" in SUPER_AGENT_INSTRUCTION
    assert '"decision"' in SUPER_AGENT_EXPECTED_OUTPUT
