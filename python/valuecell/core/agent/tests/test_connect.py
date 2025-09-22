"""
Updated tests for RemoteConnections after simplifying local/remote handling.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from valuecell.core.agent.connect import RemoteConnections, AgentContext


class TestRemoteConnectionsUnified:
    def setup_method(self):
        self.instance = RemoteConnections()

    def test_init_creates_minimal_attributes(self):
        inst = RemoteConnections()
        assert isinstance(inst._contexts, dict)
        assert isinstance(inst._agent_locks, dict)
        assert inst._remote_contexts_loaded is False
        assert len(inst._contexts) == 0

    def test_load_remote_contexts_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # invalid JSON
            (Path(temp_dir) / "invalid.json").write_text("{ invalid")

            # missing name
            (Path(temp_dir) / "no_name.json").write_text(
                json.dumps({"url": "http://localhost:8000"})
            )

            # missing url
            (Path(temp_dir) / "no_url.json").write_text(
                json.dumps({"name": "agent_without_url"})
            )

            # valid
            (Path(temp_dir) / "ok.json").write_text(
                json.dumps({"name": "remote_ok", "url": "http://localhost:9000"})
            )

            self.instance._load_remote_contexts(temp_dir)
            assert "remote_ok" in self.instance._contexts
            ctx = self.instance._contexts["remote_ok"]
            assert ctx.url == "http://localhost:9000"
            assert ctx.instance is None

    @pytest.mark.asyncio
    async def test_start_agent_local_not_found(self):
        with patch(
            "valuecell.core.agent.registry.get_agent_class_by_name", return_value=None
        ):
            with pytest.raises(ValueError, match="not found"):
                await self.instance.start_agent("nonexistent")

    @pytest.mark.asyncio
    async def test_start_agent_local_with_listener(self):
        # Mock local agent class
        mock_instance = MagicMock()
        mock_card = MagicMock()
        mock_card.url = "http://localhost:8100"
        mock_card.capabilities.push_notifications = True
        mock_instance.agent_card = mock_card

        with patch(
            "valuecell.core.agent.registry.get_agent_class_by_name",
            return_value=lambda: mock_instance,
        ):
            with patch.object(
                self.instance,
                "_start_listener",
                return_value=(
                    MagicMock(),
                    "http://localhost:5555/notify",
                ),
            ) as mock_listener:
                with patch("asyncio.create_task") as mock_task:
                    with patch("asyncio.sleep", new=AsyncMock()):
                        with patch(
                            "valuecell.core.agent.connect.AgentClient"
                        ) as mock_client:
                            result = await self.instance.start_agent(
                                "local_agent", with_listener=True, listener_port=5555
                            )

                        assert result is mock_card
                        mock_listener.assert_called_once()
                        mock_task.assert_called()  # serve()
                        mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_agent_url_only_success(self):
        # Preload a URL-only context
        self.instance._contexts["remote_agent"] = AgentContext(
            name="remote_agent", url="http://localhost:9001"
        )

        fake_card = MagicMock()
        fake_card.capabilities.push_notifications = False

        class FakeResolver:
            async def get_agent_card(self):
                return fake_card

        with patch("httpx.AsyncClient"):
            with patch(
                "valuecell.core.agent.connect.A2ACardResolver",
                return_value=FakeResolver(),
            ):
                with patch("valuecell.core.agent.connect.AgentClient") as mock_client:
                    result = await self.instance.start_agent("remote_agent")
                    assert result is fake_card
                    mock_client.assert_called_once_with(
                        "http://localhost:9001", push_notification_url=None
                    )

    def test_get_agent_card_fetch_sync(self):
        # Create url-only context; call from sync test to trigger blocking fetch
        ctx = MagicMock()
        ctx.name = "url_only"
        ctx.url = "http://localhost:9100"
        ctx.instance = None
        ctx.agent_card = None
        self.instance._contexts["url_only"] = ctx

        fake_card = MagicMock()

        class FakeResolver:
            async def get_agent_card(self):
                return fake_card

        with patch("httpx.AsyncClient"):
            with patch(
                "valuecell.core.agent.connect.A2ACardResolver",
                return_value=FakeResolver(),
            ):
                card = self.instance.get_agent_card("url_only", fetch_if_missing=True)
                assert card is fake_card
                assert ctx.agent_card is fake_card

    @pytest.mark.asyncio
    async def test_cleanup_agent(self):
        # Prepare context with async resources
        mock_client = AsyncMock()
        listener_task = asyncio.create_task(asyncio.sleep(0))
        server_task = asyncio.create_task(asyncio.sleep(0))
        # cancel promptly
        listener_task.cancel()
        server_task.cancel()

        # Build a minimal context-like object
        class Ctx:
            pass

        ctx = Ctx()
        ctx.name = "cleanme"
        ctx.client = mock_client
        ctx.listener_task = listener_task
        ctx.listener_url = "http://localhost:5555/notify"
        ctx.server_task = server_task
        ctx.instance = None
        ctx.url = "http://localhost:9999"
        ctx.agent_card = None

        self.instance._contexts["cleanme"] = ctx

        await self.instance._cleanup_agent("cleanme")
        mock_client.close.assert_called_once()
        assert "cleanme" not in self.instance._contexts

    @pytest.mark.asyncio
    async def test_get_client_starts_when_missing(self):
        with patch.object(self.instance, "start_agent") as mock_start:

            async def side_effect(name):
                # inject a context with client
                class Ctx:
                    pass

                c = Ctx()
                c.name = name
                c.client = MagicMock()
                c.instance = None
                c.url = "http://localhost:9200"
                c.agent_card = None
                c.server_task = None
                c.listener_task = None
                c.listener_url = None
                c.desired_listener_host = None
                c.desired_listener_port = None
                c.notification_callback = None
                self.instance._contexts[name] = c
                return MagicMock()

            mock_start.side_effect = side_effect
            client = await self.instance.get_client("need_client")
            assert client is self.instance._contexts["need_client"].client

    def test_list_available_only(self):
        # simulate loaded contexts
        class Ctx:
            pass

        local_ctx = Ctx()
        local_ctx.instance = MagicMock()
        local_ctx.url = None
        remote_ctx = Ctx()
        remote_ctx.instance = None
        remote_ctx.url = "http://x"
        self.instance._contexts["local_a"] = local_ctx
        self.instance._contexts["url_b"] = remote_ctx
        with patch(
            "valuecell.core.agent.registry.list_agent_names",
            return_value=["local_a", "other_local"],
        ):
            names = self.instance.list_available_agents()
            assert "local_a" in names
            assert "url_b" in names
