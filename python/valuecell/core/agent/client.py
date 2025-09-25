from typing import AsyncIterator

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, PushNotificationConfig, Role, TextPart
from valuecell.utils import generate_uuid

from ..types import RemoteAgentResponse


class AgentClient:
    """Client for communicating with remote agents via A2A protocol.

    Handles HTTP communication with remote agents, including message sending
    and agent card resolution. Supports both streaming and non-streaming modes.
    """

    def __init__(self, agent_url: str, push_notification_url: str = None):
        """Initialize the agent client.

        Args:
            agent_url: URL of the remote agent
            push_notification_url: Optional URL for push notifications
        """
        self.agent_url = agent_url
        self.push_notification_url = push_notification_url
        self.agent_card = None
        self._client = None
        self._httpx_client = None
        self._initialized = False

    async def ensure_initialized(self):
        """Ensure the client is initialized with agent card and HTTP client."""
        if not self._initialized:
            await self._setup_client()
            self._initialized = True

    async def _setup_client(self):
        """Set up the HTTP client and resolve the agent card."""
        self._httpx_client = httpx.AsyncClient(timeout=30)

        config = ClientConfig(
            httpx_client=self._httpx_client,
            accepted_output_modes=["text"],
        )

        push_notification_configs = []
        if self.push_notification_url:
            push_notification_configs.append(
                PushNotificationConfig(
                    id=generate_uuid("pushcfg"),
                    token="token",
                    url=self.push_notification_url,
                )
            )
            config.push_notification_configs = push_notification_configs
            config.streaming = False
            config.polling = True

        client_factory = ClientFactory(config)
        card_resolver = A2ACardResolver(self._httpx_client, self.agent_url)
        self.agent_card = await card_resolver.get_agent_card()
        self._client = client_factory.create(self.agent_card)

    async def send_message(
        self,
        query: str,
        conversation_id: str = None,
        metadata: dict = None,
        streaming: bool = False,
    ) -> AsyncIterator[RemoteAgentResponse]:
        """Send a message to the remote agent and return an async iterator.

        This method always returns an async iterator producing (remote_task,
        event) pairs. When `streaming` is True the iterator yields streaming
        events as they arrive. When `streaming` is False the iterator yields a
        single (task, event) pair and then completes.

        Args:
            query: The user query to send to the agent.
            conversation_id: Optional conversation id to correlate messages.
            metadata: Optional metadata to send alongside the message.
            streaming: Whether to request streaming responses from the agent.

        Returns:
            An async iterator yielding `RemoteAgentResponse` items (task,event).
        """
        await self.ensure_initialized()

        message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=query))],
            message_id=generate_uuid("msg"),
            context_id=conversation_id or generate_uuid("ctx"),
            metadata=metadata if metadata else None,
        )

        source_gen = self._client.send_message(message)

        async def wrapper() -> AsyncIterator[RemoteAgentResponse]:
            try:
                if streaming:
                    async for item in source_gen:
                        yield item
                else:
                    # yield only the first item
                    item = await source_gen.__anext__()
                    yield item
            finally:
                # ensure underlying generator is closed
                await source_gen.aclose()

        return wrapper()

    async def get_agent_card(self):
        """Get the agent card from the remote agent.

        Returns:
            The resolved agent card
        """
        await self.ensure_initialized()
        card_resolver = A2ACardResolver(self._httpx_client, self.agent_url)
        return await card_resolver.get_agent_card()

    async def close(self):
        """Close the HTTP client and clean up resources."""
        if self._httpx_client:
            await self._httpx_client.aclose()
            self._httpx_client = None
            self._client = None
            self._initialized = False
