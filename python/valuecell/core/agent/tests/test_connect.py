from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict, Optional

import pytest
from a2a.client.client_factory import minimal_agent_card
from a2a.types import AgentCard
from valuecell.core.agent import connect as connect_mod
from valuecell.core.agent.connect import RemoteConnections

# ----------------------------
# Test helpers and fakes
# ----------------------------


def make_card_dict(name: str, url: str, push_notifications: bool) -> dict:
    """Create a complete AgentCard dict with all required fields filled.

    We base this on a2a.client.client_factory.minimal_agent_card to ensure all
    required properties exist, then override name/url and capabilities.
    """
    base = minimal_agent_card(url)
    card_dict = base.model_dump()
    card_dict.update(
        {
            "name": name,
            "url": url,
            # Provide a description to be explicit (parse_local_agent_card_dict can also fill it)
            "description": f"Test card for {name}",
            # Capabilities must include push_notifications per our tests
            "capabilities": {
                "streaming": True,
                "push_notifications": push_notifications,
            },
        }
    )
    return card_dict


@dataclass
class FakeAgentClient:
    """A lightweight stand-in for AgentClient to avoid real HTTP calls.

    Behavior:
    - ensure_initialized() sets agent_card from the url->AgentCard mapping.
    - close() marks the instance as closed.
    """

    # Class-level registry populated by tests: url -> AgentCard
    cards_by_url: ClassVar[Dict[str, AgentCard]] = {}
    # Class-level counter to validate single instantiation in concurrency tests
    create_count: ClassVar[int] = 0

    agent_url: str
    push_notification_url: Optional[str] = None

    def __init__(self, agent_url: str, push_notification_url: str | None = None):
        type(self).create_count += 1
        self.agent_url = agent_url
        self.push_notification_url = push_notification_url
        self.agent_card: Optional[AgentCard] = None
        self._closed = False

    async def ensure_initialized(self):
        # Simulate I/O a little
        await asyncio.sleep(0)
        # Map back to the card provided in the JSON for this URL
        card = type(self).cards_by_url.get(self.agent_url)
        if card is None:
            # As a fallback, generate a minimal card to keep tests robust
            card = minimal_agent_card(self.agent_url)
        self.agent_card = card

    async def close(self):
        self._closed = True


class DummyNotificationListener:
    """Dummy listener that doesn't bind a real port."""

    def __init__(
        self, host: str = "localhost", port: int = 0, notification_callback=None
    ):
        self.host = host
        self.port = port
        self.notification_callback = notification_callback

    async def start_async(self):
        # Simulate server startup without actually starting uvicorn
        await asyncio.sleep(0.01)


# ----------------------------
# Tests
# ----------------------------


@pytest.mark.asyncio
async def test_load_from_dir_and_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Prepare two agent cards
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)

    cards = [
        make_card_dict("AgentAlpha", "http://127.0.0.1:8101", push_notifications=False),
        make_card_dict("AgentBeta", "http://127.0.0.1:8102", push_notifications=True),
    ]
    for c in cards:
        with open(dir_path / f"{c['name']}.json", "w", encoding="utf-8") as f:
            json.dump(c, f)

    # Wire FakeAgentClient and DummyNotificationListener
    monkeypatch.setattr(connect_mod, "AgentClient", FakeAgentClient)
    monkeypatch.setattr(connect_mod, "NotificationListener", DummyNotificationListener)

    # Also prime the client mapping
    FakeAgentClient.cards_by_url = {
        c["url"]: AgentCard.model_validate(c) for c in cards
    }
    FakeAgentClient.create_count = 0

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    all_agents = rc.list_available_agents()
    assert set(all_agents) == {"AgentAlpha", "AgentBeta"}


@pytest.mark.asyncio
async def test_start_agent_without_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Create a card that does not support push notifications
    card = make_card_dict(
        "NoPushAgent", "http://127.0.0.1:8201", push_notifications=False
    )
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)
    with open(dir_path / f"{card['name']}.json", "w", encoding="utf-8") as f:
        json.dump(card, f)

    monkeypatch.setattr(connect_mod, "AgentClient", FakeAgentClient)
    monkeypatch.setattr(connect_mod, "NotificationListener", DummyNotificationListener)
    FakeAgentClient.cards_by_url = {card["url"]: AgentCard.model_validate(card)}
    FakeAgentClient.create_count = 0

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    returned_card = await rc.start_agent("NoPushAgent", with_listener=False)
    assert isinstance(returned_card, AgentCard)
    assert returned_card.name == "NoPushAgent"

    # Validate client exists and was created exactly once
    client = await rc.get_client("NoPushAgent")
    assert isinstance(client, FakeAgentClient)
    assert client.push_notification_url is None  # listener not requested
    assert FakeAgentClient.create_count == 1


@pytest.mark.asyncio
async def test_start_agent_with_listener_when_supported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Card supports push notifications
    card = make_card_dict("PushAgent", "http://127.0.0.1:8301", push_notifications=True)
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)
    with open(dir_path / f"{card['name']}.json", "w", encoding="utf-8") as f:
        json.dump(card, f)

    monkeypatch.setattr(connect_mod, "AgentClient", FakeAgentClient)
    monkeypatch.setattr(connect_mod, "NotificationListener", DummyNotificationListener)
    FakeAgentClient.cards_by_url = {card["url"]: AgentCard.model_validate(card)}
    FakeAgentClient.create_count = 0

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    returned_card = await rc.start_agent(
        "PushAgent", with_listener=True, listener_host="127.0.0.1"
    )
    assert isinstance(returned_card, AgentCard)
    assert returned_card.name == "PushAgent"

    # Ensure listener started and URL recorded
    ctx = rc._contexts["PushAgent"]
    assert ctx.listener_url is not None
    assert ctx.listener_url.startswith("http://127.0.0.1:")

    # Current implementation creates client before listener, so push_notification_url stays None
    client = await rc.get_client("PushAgent")
    assert isinstance(client, FakeAgentClient)
    assert client.push_notification_url is None


@pytest.mark.asyncio
async def test_start_agent_failure_does_not_set_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Arrange a card and a failing client ensure_initialized
    card = make_card_dict(
        "FailAgent", "http://127.0.0.1:8399", push_notifications=False
    )
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)
    with open(dir_path / f"{card['name']}.json", "w", encoding="utf-8") as f:
        json.dump(card, f)

    class FailingClient(FakeAgentClient):
        async def ensure_initialized(self):
            raise RuntimeError("resolver failed")

    monkeypatch.setattr(connect_mod, "AgentClient", FailingClient)
    monkeypatch.setattr(connect_mod, "NotificationListener", DummyNotificationListener)

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    with pytest.raises(RuntimeError, match="failed"):
        await rc.start_agent("FailAgent", with_listener=False)

    assert "FailAgent" not in rc.list_running_agents()


@pytest.mark.asyncio
async def test_start_agent_with_listener_but_not_supported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Card does NOT support push notifications; listener should not be started
    card = make_card_dict("NoPush", "http://127.0.0.1:8401", push_notifications=False)
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)
    with open(dir_path / f"{card['name']}.json", "w", encoding="utf-8") as f:
        json.dump(card, f)

    monkeypatch.setattr(connect_mod, "AgentClient", FakeAgentClient)
    monkeypatch.setattr(connect_mod, "NotificationListener", DummyNotificationListener)
    FakeAgentClient.cards_by_url = {card["url"]: AgentCard.model_validate(card)}

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    await rc.start_agent("NoPush", with_listener=True)
    client = await rc.get_client("NoPush")
    assert isinstance(client, FakeAgentClient)
    # Since capabilities.push_notifications=False, listener shouldn't be used
    assert client.push_notification_url is None


@pytest.mark.asyncio
async def test_concurrent_start_calls_single_initialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    card = make_card_dict(
        "ConcurrentAgent", "http://127.0.0.1:8501", push_notifications=True
    )
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)
    with open(dir_path / f"{card['name']}.json", "w", encoding="utf-8") as f:
        json.dump(card, f)

    monkeypatch.setattr(connect_mod, "AgentClient", FakeAgentClient)
    monkeypatch.setattr(connect_mod, "NotificationListener", DummyNotificationListener)
    FakeAgentClient.cards_by_url = {card["url"]: AgentCard.model_validate(card)}
    FakeAgentClient.create_count = 0

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    # Launch multiple concurrent start calls for the same agent
    await asyncio.gather(
        rc.start_agent("ConcurrentAgent", with_listener=True),
        rc.start_agent("ConcurrentAgent", with_listener=True),
        rc.start_agent("ConcurrentAgent", with_listener=True),
    )

    # Only one client should have been constructed
    assert FakeAgentClient.create_count == 1


@pytest.mark.asyncio
async def test_stop_agent_and_stop_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    card1 = make_card_dict("A1", "http://127.0.0.1:8601", push_notifications=True)
    card2 = make_card_dict("A2", "http://127.0.0.1:8602", push_notifications=False)
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)
    for c in (card1, card2):
        with open(dir_path / f"{c['name']}.json", "w", encoding="utf-8") as f:
            json.dump(c, f)

    monkeypatch.setattr(connect_mod, "AgentClient", FakeAgentClient)
    monkeypatch.setattr(connect_mod, "NotificationListener", DummyNotificationListener)
    FakeAgentClient.cards_by_url = {
        card1["url"]: AgentCard.model_validate(card1),
        card2["url"]: AgentCard.model_validate(card2),
    }

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    await rc.start_agent("A1", with_listener=True)
    await rc.start_agent("A2", with_listener=False)
    assert set(rc.list_running_agents()) == {"A1", "A2"}

    # Stop a single agent
    await rc.stop_agent("A1")
    assert rc.list_running_agents() == ["A2"]

    # Stop all
    await rc.stop_all()
    assert rc.list_running_agents() == []


@pytest.mark.asyncio
async def test_unknown_agent_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Empty directory (no cards)
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)

    monkeypatch.setattr(connect_mod, "AgentClient", FakeAgentClient)

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    with pytest.raises(ValueError):
        await rc.start_agent("NotExist")


def _write_card(path: Path, card_dict: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(card_dict, f)


@pytest.mark.asyncio
async def test_disabled_agents_are_skipped(tmp_path: Path):
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)

    enabled_card = make_card_dict("EnabledAgent", "http://127.0.0.1:8701", True)
    disabled_card = make_card_dict("DisabledAgent", "http://127.0.0.1:8702", True)
    disabled_card["enabled"] = False

    _write_card(dir_path / "EnabledAgent.json", enabled_card)
    _write_card(dir_path / "DisabledAgent.json", disabled_card)

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    assert rc.list_available_agents() == ["EnabledAgent"]


@pytest.mark.asyncio
async def test_get_all_agent_cards_returns_local_cards(tmp_path: Path):
    dir_path = tmp_path / "agent_cards"
    dir_path.mkdir(parents=True)

    cards = [
        make_card_dict("CardOne", "http://127.0.0.1:8801", False),
        make_card_dict("CardTwo", "http://127.0.0.1:8802", True),
    ]

    for card in cards:
        _write_card(dir_path / f"{card['name']}.json", card)

    rc = RemoteConnections()
    rc.load_from_dir(str(dir_path))

    all_cards = rc.get_all_agent_cards()

    assert set(all_cards.keys()) == {"CardOne", "CardTwo"}
    assert all(isinstance(card, AgentCard) for card in all_cards.values())
