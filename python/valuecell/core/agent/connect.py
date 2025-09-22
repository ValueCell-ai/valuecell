import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from a2a.types import AgentCard
from valuecell.core.agent.card import parse_local_agent_card_dict
from valuecell.core.agent.client import AgentClient
from valuecell.core.agent.listener import NotificationListener
from valuecell.core.types import NotificationCallbackType
from valuecell.utils import get_next_available_port

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Unified context for remote agents."""

    name: str
    # Connection/runtime state
    url: Optional[str] = None
    local_agent_card: Optional[AgentCard] = None
    # Capability flags derived from card or JSON (fallbacks if no full card)
    listener_task: Optional[asyncio.Task] = None
    listener_url: Optional[str] = None
    client: Optional[AgentClient] = None
    # Listener preferences
    desired_listener_host: Optional[str] = None
    desired_listener_port: Optional[int] = None
    notification_callback: Optional[NotificationCallbackType] = None


class RemoteConnections:
    """Manager for remote Agent connections (client + optional listener only).

    Design: This class no longer starts any local in-process agents or talks to
    a registry. It reads AgentCards from local JSON files under
    python/configs/agent_cards, creates HTTP clients to the specified URLs, and
    optionally starts a notification listener when supported.
    """

    def __init__(self):
        # Unified per-agent contexts (keyed by agent name)
        self._contexts: Dict[str, AgentContext] = {}
        # Whether remote contexts (from configs) have been loaded
        self._remote_contexts_loaded: bool = False
        # Per-agent locks for concurrent start_agent calls
        self._agent_locks: Dict[str, asyncio.Lock] = {}

    def _get_agent_lock(self, agent_name: str) -> asyncio.Lock:
        """Get or create a lock for a specific agent (thread-safe)"""
        if agent_name not in self._agent_locks:
            self._agent_locks[agent_name] = asyncio.Lock()
        return self._agent_locks[agent_name]

    def _load_remote_contexts(self, agent_card_dir: str = None) -> None:
        """Load remote agent contexts from JSON config files into _contexts.

        Always uses parse_local_agent_card_dict to parse/normalize the
        AgentCard; supports custom directories via base_dir.
        """
        if agent_card_dir is None:
            # Default to python/configs/agent_cards relative to current file
            agent_card_dir = (
                Path(__file__).parent.parent.parent.parent / "configs" / "agent_cards"
            )
        else:
            agent_card_dir = Path(agent_card_dir)

        if not agent_card_dir.exists():
            self._remote_contexts_loaded = True
            logger.warning(
                f"Agent card directory {agent_card_dir} does not exist; no remote agents loaded"
            )
            return

        for json_file in agent_card_dir.glob("*.json"):
            try:
                # Read name minimally to resolve via helper
                with open(json_file, "r", encoding="utf-8") as f:
                    agent_card_dict = json.load(f)
                agent_name = agent_card_dict.get("name")
                if not agent_name:
                    continue
                local_agent_card = parse_local_agent_card_dict(agent_card_dict)
                if not local_agent_card or not local_agent_card.url:
                    continue
                self._contexts[agent_name] = AgentContext(
                    name=agent_name,
                    url=local_agent_card.url,
                    local_agent_card=local_agent_card,
                )
            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                logger.warning(
                    f"Failed to load agent card from {json_file}; skipping: {e}"
                )
                continue
        self._remote_contexts_loaded = True

    def _ensure_remote_contexts_loaded(self) -> None:
        if not self._remote_contexts_loaded:
            self._load_remote_contexts()

    # Public helper primarily for tests or tooling to load from a custom dir
    def load_from_dir(self, config_dir: str) -> None:
        """Load agent contexts from a specific directory of JSON card files."""
        self._load_remote_contexts(config_dir)

    async def start_agent(
        self,
        agent_name: str,
        with_listener: bool = True,
        listener_port: int | None = None,
        listener_host: str = "localhost",
        notification_callback: NotificationCallbackType = None,
    ) -> Optional[AgentCard]:
        """Connect to an agent URL and optionally start a notification listener.

        Returns the AgentCard if available from local configs; otherwise None.
        """
        # Use agent-specific lock to prevent concurrent starts of the same agent
        agent_lock = self._get_agent_lock(agent_name)
        async with agent_lock:
            ctx = await self._get_or_create_context(agent_name)

            # Record listener preferences on the context
            if with_listener:
                ctx.desired_listener_host = listener_host
                ctx.desired_listener_port = listener_port
                ctx.notification_callback = notification_callback

            # If already connected, return card (may be None if only URL known)
            if ctx.client:
                return ctx.client.agent_card

            # Ensure client connection (uses URL from context)
            await self._ensure_client(ctx)

            # Ensure listener if requested and supported
            if with_listener:
                await self._ensure_listener(ctx)

            return ctx.client.agent_card

    async def _ensure_listener(self, ctx: AgentContext) -> None:
        """Ensure listener is running if supported by agent card."""
        if ctx.listener_task:
            return
        if (
            ctx.client
            and ctx.client.agent_card
            and not ctx.client.agent_card.capabilities.push_notifications
        ):
            return
        try:
            listener_task, listener_url = await self._start_listener(
                host=ctx.desired_listener_host or "localhost",
                port=ctx.desired_listener_port,
                notification_callback=ctx.notification_callback,
            )
            ctx.listener_task = listener_task
            ctx.listener_url = listener_url
        except Exception as e:
            logger.error(f"Failed to start listener for '{ctx.name}': {e}")
            raise RuntimeError(f"Failed to start listener for '{ctx.name}'") from e

    async def _ensure_client(self, ctx: AgentContext) -> None:
        """Ensure AgentClient is created and connected."""
        if ctx.client:
            return
        url = ctx.url or (ctx.local_agent_card.url if ctx.local_agent_card else None)
        if not url:
            raise ValueError(f"Unable to determine URL for agent '{ctx.name}'")
        ctx.client = AgentClient(url, push_notification_url=ctx.listener_url)
        await ctx.client.ensure_initialized()
        logger.info(f"Connected to agent '{ctx.name}' at {url}")
        if ctx.listener_url:
            logger.info(f"  └─ with listener at {ctx.listener_url}")

    async def _start_listener(
        self,
        host: str = "localhost",
        port: Optional[int] = None,
        notification_callback: callable = None,
    ) -> tuple[asyncio.Task, str]:
        """Start a NotificationListener and return (task, url)."""
        if port is None:
            port = get_next_available_port(5000)
        listener = NotificationListener(
            host=host,
            port=port,
            notification_callback=notification_callback,
        )
        listener_task = asyncio.create_task(listener.start_async())
        listener_url = f"http://{host}:{port}/notify"
        await asyncio.sleep(0.3)
        logger.info(f"Started listener at {listener_url}")
        return listener_task, listener_url

    async def _get_or_create_context(
        self,
        agent_name: str,
    ) -> AgentContext:
        """Get an AgentContext for a known agent (from local configs)."""
        # Load remote contexts lazily
        self._ensure_remote_contexts_loaded()

        ctx = self._contexts.get(agent_name)
        if ctx:
            return ctx

        # If not local and not preloaded as remote, it's unknown
        raise ValueError(
            f"Agent '{agent_name}' not found (neither local nor remote config)"
        )

    async def _cleanup_agent(self, agent_name: str):
        """Clean up all resources for an agent"""
        ctx = self._contexts.get(agent_name)
        if not ctx:
            return
        # Close client
        if ctx.client:
            await ctx.client.close()
            ctx.client = None
        # Stop listener
        if ctx.listener_task:
            ctx.listener_task.cancel()
            try:
                await ctx.listener_task
            except asyncio.CancelledError:
                pass
            ctx.listener_task = None
            ctx.listener_url = None
        # Keep the context to allow quick reconnection; do not delete metadata
        # Removing deletion allows list_available_agents to remain stable

    async def get_client(self, agent_name: str) -> AgentClient:
        """Get Agent client connection"""
        ctx = self._contexts.get(agent_name)
        if not ctx or not ctx.client:
            await self.start_agent(agent_name)
            ctx = self._contexts.get(agent_name)
        return ctx.client

    async def stop_agent(self, agent_name: str):
        """Stop Agent service and associated listener"""
        await self._cleanup_agent(agent_name)
        logger.info(f"Stopped agent '{agent_name}' and its listener")

    def list_running_agents(self) -> List[str]:
        """List running agents"""
        return [name for name, ctx in self._contexts.items() if ctx.client]

    def list_available_agents(self) -> List[str]:
        """List all available agents from local config cards"""
        # Ensure remote contexts are loaded
        self._ensure_remote_contexts_loaded()
        return list(self._contexts.keys())

    async def stop_all(self):
        """Stop all running clients and listeners"""
        for agent_name in list(self._contexts.keys()):
            await self.stop_agent(agent_name)

    def get_agent_card(self, agent_name: str) -> Optional[AgentCard]:
        """Get AgentCard for a known agent from local configs."""
        self._ensure_remote_contexts_loaded()
        ctx = self._contexts.get(agent_name)
        if not ctx:
            return None
        if ctx.client and ctx.client.agent_card:
            return ctx.client.agent_card
        if ctx.local_agent_card:
            return ctx.local_agent_card
        return None


# Global default instance for backward compatibility and ease of use
_default_remote_connections = RemoteConnections()


# Convenience functions that delegate to the default instance
def get_default_remote_connections() -> RemoteConnections:
    """Get the default RemoteConnections instance"""
    return _default_remote_connections
