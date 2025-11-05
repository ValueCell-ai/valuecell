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
    """Unified context for remote agents.

    Stores connection state, URLs, and configuration for a remote agent.
    """

    name: str
    # Connection/runtime state
    url: Optional[str] = None
    local_agent_card: Optional[AgentCard] = None
    # Capability flags derived from card or JSON (fallbacks if no full card)
    listener_task: Optional[asyncio.Task] = None
    listener_url: Optional[str] = None
    client: Optional[AgentClient] = None
    # Planner passthrough flag derived from raw agent card JSON
    planner_passthrough: bool = False
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
                if not agent_card_dict.get("enabled", True):
                    continue
                # Detect planner passthrough from raw JSON (top-level or metadata)
                passthrough = bool(agent_card_dict.get("planner_passthrough"))
                if not passthrough:
                    meta = agent_card_dict.get("metadata") or {}
                    if isinstance(meta, dict):
                        passthrough = bool(meta.get("planner_passthrough"))
                local_agent_card = parse_local_agent_card_dict(agent_card_dict)
                if not local_agent_card:
                    continue
                self._contexts[agent_name] = AgentContext(
                    name=agent_name,
                    url=local_agent_card.url,
                    local_agent_card=local_agent_card,
                    planner_passthrough=passthrough,
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

            # If already connected, return card
            if ctx.client and ctx.client.agent_card:
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
        # Only treat as connected if a client exists AND has a resolved agent_card
        if ctx.client and getattr(ctx.client, "agent_card", None):
            return
        url = ctx.url or (ctx.local_agent_card.url if ctx.local_agent_card else None)
        if not url:
            raise ValueError(f"Unable to determine URL for agent '{ctx.name}'")
        # Initialize a temporary client; only assign to context on success
        tmp_client = AgentClient(url, push_notification_url=ctx.listener_url)
        try:
            await tmp_client.ensure_initialized()
            # Ensure agent card was resolved by the resolver
            if not getattr(tmp_client, "agent_card", None):
                raise RuntimeError("Agent card resolution returned None")
            # Success: assign to context
            ctx.client = tmp_client
            logger.info(f"Connected to agent '{ctx.name}' at {url}")
            if ctx.listener_url:
                logger.info(f"  └─ with listener at {ctx.listener_url}")
        except Exception as e:
            # Defensive: close any underlying resources of the temporary client
            try:
                await tmp_client.close()
            except Exception:
                pass
            logger.error(f"Failed to initialize client for '{ctx.name}' at {url}: {e}")
            raise

    async def _start_listener(
        self,
        host: str = "localhost",
        port: Optional[int] = None,
        notification_callback: NotificationCallbackType = None,
    ) -> tuple[asyncio.Task, str]:
        """Start a NotificationListener and return (task, url).

        Args:
            host: Host to bind the listener to.
            port: Optional port to bind; if None a free port will be selected.
            notification_callback: Callback invoked when notifications arrive;
                should conform to `NotificationCallbackType`.

        Returns:
            Tuple of (asyncio.Task, listener_url) where listener_url is the
            http URL where notifications should be posted.
        """
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
        # An agent is considered running only if the client exists and has a resolved card
        return [
            name
            for name, ctx in self._contexts.items()
            if ctx.client and getattr(ctx.client, "agent_card", None)
        ]

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

    def get_all_agent_cards(self) -> Dict[str, AgentCard]:
        """Get all AgentCards for known agents from local configs.

        Returns:
            Dict mapping agent names to their AgentCard objects.
        """
        self._ensure_remote_contexts_loaded()
        agent_cards = {}
        for name, _ in self._contexts.items():
            card = self.get_agent_card(name)
            if card:
                agent_cards[name] = card

        return agent_cards

    def is_planner_passthrough(self, agent_name: str) -> bool:
        """Return True if the named agent is marked as planner passthrough.

        The flag is read once from raw JSON on load and cached in AgentContext.
        """
        self._ensure_remote_contexts_loaded()
        ctx = self._contexts.get(agent_name)
        return bool(getattr(ctx, "planner_passthrough", False)) if ctx else False
