"""
Unit tests for SuperAgent model consistency detection and restart logic.
"""

from __future__ import annotations

import pytest

import valuecell.core.super_agent.core as super_agent_mod


class DummyModel:
    def __init__(self, mid: str, provider: str):
        self.id = mid
        self.provider = provider


class StubAgent:
    def __init__(self, model, **kwargs):
        # keep minimal surface: just store the model for inspection
        self.model = model
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def stub_agent_class(monkeypatch: pytest.MonkeyPatch):
    # Replace real Agent with a stub to avoid external dependencies
    monkeypatch.setattr(super_agent_mod, "Agent", StubAgent)
    # Make json-mode decision deterministic and lightweight
    monkeypatch.setattr(
        super_agent_mod.model_utils_mod, "model_should_use_json_mode", lambda _m: False
    )


def test_init_builds_agent_with_expected_model(monkeypatch: pytest.MonkeyPatch):
    # Arrange
    expected = DummyModel("m1", "p1")
    monkeypatch.setattr(
        super_agent_mod.model_utils_mod,
        "get_model_for_agent",
        lambda name: expected if name == "super_agent" else None,
    )

    sa = super_agent_mod.SuperAgent()

    # Act
    agent = sa._get_or_init_agent()

    # Assert
    assert agent is not None
    assert agent.model is expected
    assert agent.model.id == "m1"
    assert agent.model.provider == "p1"


def test_restart_when_model_differs(monkeypatch: pytest.MonkeyPatch):
    # Arrange: current agent has old model
    sa = super_agent_mod.SuperAgent()
    current = DummyModel("old", "p1")
    sa.agent = StubAgent(current)

    expected = DummyModel("new", "p1")
    monkeypatch.setattr(
        super_agent_mod.model_utils_mod,
        "get_model_for_agent",
        lambda _name: expected,
    )

    # Act
    agent = sa._get_or_init_agent()

    # Assert: agent replaced with new model
    assert agent is not None
    assert agent.model is expected
    assert agent.model.id == "new"
    assert agent.model.provider == "p1"


def test_keep_agent_when_model_same(monkeypatch: pytest.MonkeyPatch):
    # Arrange: current and expected models match on id+provider
    sa = super_agent_mod.SuperAgent()
    current = DummyModel("same", "p1")
    old_agent = StubAgent(current)
    sa.agent = old_agent

    expected = DummyModel("same", "p1")
    monkeypatch.setattr(
        super_agent_mod.model_utils_mod,
        "get_model_for_agent",
        lambda _name: expected,
    )

    # Act
    agent = sa._get_or_init_agent()

    # Assert: no restart; instance identity is preserved
    assert agent is old_agent
    assert agent.model.id == "same"
    assert agent.model.provider == "p1"


def test_init_returns_none_when_expected_model_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    # Arrange: model resolution fails
    def _raise(*_a, **_k):
        raise RuntimeError("no model")

    monkeypatch.setattr(super_agent_mod.model_utils_mod, "get_model_for_agent", _raise)

    sa = super_agent_mod.SuperAgent()

    # Act
    agent = sa._get_or_init_agent()

    # Assert
    assert agent is None


def test_existing_agent_kept_when_model_resolution_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    # Arrange: model resolution fails but an agent already exists
    def _raise(*_a, **_k):
        raise RuntimeError("no model")

    monkeypatch.setattr(super_agent_mod.model_utils_mod, "get_model_for_agent", _raise)

    sa = super_agent_mod.SuperAgent()
    current = DummyModel("old", "p1")
    old_agent = StubAgent(current)
    sa.agent = old_agent

    # Act
    agent = sa._get_or_init_agent()

    # Assert: existing agent is preserved
    assert agent is old_agent
    assert agent.model.id == "old"


def test_restart_failure_keeps_existing_agent(monkeypatch: pytest.MonkeyPatch):
    # Arrange: expected model differs, but Agent construction fails
    sa = super_agent_mod.SuperAgent()
    current = DummyModel("old", "p1")
    old_agent = StubAgent(current)
    sa.agent = old_agent

    expected = DummyModel("new", "p1")
    monkeypatch.setattr(
        super_agent_mod.model_utils_mod,
        "get_model_for_agent",
        lambda _name: expected,
    )

    class FailingAgent:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    # Replace Agent with failing constructor just for this restart
    monkeypatch.setattr(super_agent_mod, "Agent", FailingAgent)

    # Act
    agent = sa._get_or_init_agent()

    # Assert: keep old agent on failure
    assert agent is old_agent
    assert agent.model.id == "old"
