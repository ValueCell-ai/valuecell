"""
Unit tests for valuecell.core.agent.client module
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from a2a.types import AgentCard, AgentCapabilities

from valuecell.core.agent.client import AgentClient


class TestAgentClient:
    """Test AgentClient class."""

    def test_init(self):
        """Test AgentClient initialization."""
        client = AgentClient("http://localhost:8000", "http://localhost:8001")

        assert client.agent_url == "http://localhost:8000"
        assert client.push_notification_url == "http://localhost:8001"
        assert client.agent_card is None
        assert client._client is None
        assert client._httpx_client is None
        assert client._initialized is False

    def test_init_without_push_url(self):
        """Test AgentClient initialization without push notification URL."""
        client = AgentClient("http://localhost:8000")

        assert client.agent_url == "http://localhost:8000"
        assert client.push_notification_url is None

    @pytest.mark.asyncio
    async def test_ensure_initialized_once(self):
        """Test that ensure_initialized only runs setup once."""
        client = AgentClient("http://localhost:8000")

        with patch.object(
            client, "_setup_client", new_callable=AsyncMock
        ) as mock_setup:
            await client.ensure_initialized()
            assert client._initialized is True
            mock_setup.assert_called_once()

            # Call again, should not setup again
            await client.ensure_initialized()
            mock_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_client_with_push_notifications(self):
        """Test _setup_client with push notification URL."""
        client = AgentClient("http://localhost:8000", "http://localhost:8001")

        mock_card = AgentCard(
            name="test_agent",
            url="http://localhost:8000",
            description="Test agent",
            capabilities=AgentCapabilities(streaming=True, push_notifications=True),
            default_input_modes=["text"],
            default_output_modes=["text"],
            version="1.0.0",
            skills=[
                {
                    "id": "test_skill",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "tags": ["test"],
                }
            ],
        )

        with (
            patch("httpx.AsyncClient") as mock_httpx_client,
            patch("valuecell.core.agent.client.ClientFactory") as mock_client_factory,
            patch(
                "valuecell.core.agent.client.A2ACardResolver"
            ) as mock_card_resolver_class,
        ):
            mock_httpx_instance = MagicMock()
            mock_httpx_client.return_value = mock_httpx_instance

            # Mock the entire A2ACardResolver instance
            mock_resolver_instance = MagicMock()
            mock_resolver_instance.get_agent_card = AsyncMock(return_value=mock_card)
            mock_card_resolver_class.return_value = mock_resolver_instance

            mock_client_instance = MagicMock()
            mock_factory_instance = MagicMock()
            mock_factory_instance.create.return_value = mock_client_instance
            mock_client_factory.return_value = mock_factory_instance

            await client._setup_client()

            # Verify httpx client was created
            mock_httpx_client.assert_called_once_with(timeout=30)

            # Verify card resolver was created and called
            mock_card_resolver_class.assert_called_once_with(
                mock_httpx_instance, "http://localhost:8000"
            )
            mock_resolver_instance.get_agent_card.assert_called_once()

            # Verify client factory was configured with push notifications
            mock_client_factory.assert_called_once()
            factory_call_args = mock_client_factory.call_args[0][0]
            assert factory_call_args.push_notification_configs is not None
            assert len(factory_call_args.push_notification_configs) == 1
            assert factory_call_args.streaming is False
            assert factory_call_args.polling is True

            # Verify client was created
            mock_factory_instance.create.assert_called_once_with(mock_card)

            # Verify instance variables were set
            assert client.agent_card == mock_card
            assert client._client == mock_client_instance

    @pytest.mark.asyncio
    async def test_setup_client_without_push_notifications(self):
        """Test _setup_client without push notification URL."""
        client = AgentClient("http://localhost:8000")

        mock_card = AgentCard(
            name="test_agent",
            url="http://localhost:8000",
            description="Test agent",
            capabilities=AgentCapabilities(streaming=True, push_notifications=False),
            default_input_modes=["text"],
            default_output_modes=["text"],
            version="1.0.0",
            skills=[
                {
                    "id": "test_skill",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "tags": ["test"],
                }
            ],
        )

        with (
            patch("httpx.AsyncClient") as mock_httpx_client,
            patch("valuecell.core.agent.client.ClientFactory") as mock_client_factory,
            patch(
                "valuecell.core.agent.client.A2ACardResolver"
            ) as mock_card_resolver_class,
        ):
            mock_httpx_instance = MagicMock()
            mock_httpx_client.return_value = mock_httpx_instance

            mock_resolver_instance = MagicMock()
            mock_resolver_instance.get_agent_card = AsyncMock(return_value=mock_card)
            mock_card_resolver_class.return_value = mock_resolver_instance

            mock_client_instance = MagicMock()
            mock_factory_instance = MagicMock()
            mock_factory_instance.create.return_value = mock_client_instance
            mock_client_factory.return_value = mock_factory_instance

            await client._setup_client()

            # Verify client factory was configured without push notifications
            mock_client_factory.assert_called_once()
            factory_call_args = mock_client_factory.call_args[0][0]
            assert factory_call_args.push_notification_configs == []
            assert factory_call_args.streaming is True  # Default value
            assert factory_call_args.polling is False  # Default value

    @pytest.mark.asyncio
    async def test_send_message_non_streaming_yields_first_and_closes(self):
        """send_message(streaming=False) should yield first item then close the source gen."""
        client = AgentClient("http://localhost:8000")

        # Bypass real setup
        with patch.object(client, "ensure_initialized", new_callable=AsyncMock):
            # Build a fake async iterator with controllable behavior
            class FakeGen:
                def __init__(self):
                    self.items = [("task1", "event1"), ("task2", "event2")]
                    self.index = 0
                    self.closed = False

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.index >= len(self.items):
                        raise StopAsyncIteration
                    item = self.items[self.index]
                    self.index += 1
                    return item

                async def aclose(self):
                    self.closed = True

            fake_gen = FakeGen()
            client._client = MagicMock()
            client._client.send_message.return_value = fake_gen

            # Call and get first item
            agen = await client.send_message("hello", streaming=False)
            first = None
            async for i in agen:
                first = i
            assert first == ("task1", "event1")
            # Ensure generator was closed
            assert fake_gen.closed is True

    @pytest.mark.asyncio
    async def test_send_message_streaming_yields_all_and_closes(self):
        """send_message(streaming=True) should stream all items and close the source gen."""
        client = AgentClient("http://localhost:8000")

        with patch.object(client, "ensure_initialized", new_callable=AsyncMock):

            class FakeGen:
                def __init__(self):
                    self.items = [("t1", "e1"), ("t2", "e2")]
                    self.index = 0
                    self.closed = False

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.index >= len(self.items):
                        raise StopAsyncIteration
                    item = self.items[self.index]
                    self.index += 1
                    return item

                async def aclose(self):
                    self.closed = True

            fake_gen = FakeGen()
            client._client = MagicMock()
            client._client.send_message.return_value = fake_gen

            agen = await client.send_message("hello", streaming=True)
            out = []
            async for i in agen:
                out.append(i)
            assert out == [("t1", "e1"), ("t2", "e2")]
            assert fake_gen.closed is True

    @pytest.mark.asyncio
    async def test_close_closes_httpx_and_resets_state(self):
        """close should close underlying httpx client and reset state flags."""
        client = AgentClient("http://localhost:8000")
        # Pretend setup has happened
        fake_httpx = MagicMock()
        fake_httpx.aclose = AsyncMock()
        client._httpx_client = fake_httpx
        client._client = MagicMock()
        client._initialized = True

        await client.close()
        fake_httpx.aclose.assert_called_once()
        assert client._httpx_client is None
        assert client._client is None
        assert client._initialized is False

    @pytest.mark.asyncio
    async def test_ensure_initialized_card_resolution_failure(self):
        """Test that ensure_initialized raises RuntimeError with helpful message on card resolution failure."""
        client = AgentClient("http://invalid-url.com")

        with (
            patch("valuecell.core.agent.client.A2ACardResolver") as mock_resolver_class,
            patch("httpx.AsyncClient"),
        ):
            mock_resolver = mock_resolver_class.return_value
            mock_resolver.get_agent_card = AsyncMock(
                side_effect=Exception("Connection timeout")
            )

            with pytest.raises(RuntimeError) as exc_info:
                await client.ensure_initialized()

            error_message = str(exc_info.value)
            assert "Failed to resolve agent card" in error_message
            assert "Check the agent logs" in error_message
            assert "Connection timeout" in str(
                exc_info.value.__cause__
            )  # Original exception should be chained
