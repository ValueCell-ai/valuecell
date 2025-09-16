from typing import AsyncIterator

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, PushNotificationConfig, Role, TextPart
from valuecell.utils import generate_uuid

from ..types import RemoteAgentResponse


class AgentClient:
    def __init__(self, agent_url: str, push_notification_url: str = None):
        self.agent_url = agent_url
        self.push_notification_url = push_notification_url
        self._client = None
        self._httpx_client = None
        self._initialized = False

    async def _ensure_initialized(self):
        if not self._initialized:
            await self._setup_client()
            self._initialized = True

    async def _setup_client(self):
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
        card = await card_resolver.get_agent_card()
        self._client = client_factory.create(card)

    async def send_message(
        self,
        query: str,
        context_id: str = None,
        metadata: dict = None,
        streaming: bool = False,
    ) -> AsyncIterator[RemoteAgentResponse]:
        """Send message to Agent.

        If `streaming` is True, return an async iterator producing (task, event) pairs.
        If `streaming` is False, return the first (task, event) pair (and close the generator).
        """
        await self._ensure_initialized()

        message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=query))],
            message_id=generate_uuid("msg"),
            context_id=context_id or generate_uuid("ctx"),
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
        await self._ensure_initialized()
        card_resolver = A2ACardResolver(self._httpx_client, self.agent_url)
        return await card_resolver.get_agent_card()

    async def close(self):
        if self._httpx_client:
            await self._httpx_client.aclose()
            self._httpx_client = None
            self._client = None
            self._initialized = False
