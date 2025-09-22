import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from a2a.client import A2ACardResolver
from a2a.types import AgentCard
from valuecell.core.agent import registry
from valuecell.core.agent.client import AgentClient
from valuecell.core.agent.listener import NotificationListener
from valuecell.core.types import NotificationCallbackType
from valuecell.utils import get_next_available_port

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Unified context for both local and remote agents."""

    name: str
    # Connection/runtime state
    url: Optional[str] = None
    agent_card: Optional[AgentCard] = None
    instance: Optional[object] = None  # when present, treated as local service
    server_task: Optional[asyncio.Task] = None
    listener_task: Optional[asyncio.Task] = None
    listener_url: Optional[str] = None
    client: Optional[AgentClient] = None
    # Listener preferences
    desired_listener_host: Optional[str] = None
    desired_listener_port: Optional[int] = None
    notification_callback: Optional[NotificationCallbackType] = None


class RemoteConnections:
    """Manager for remote Agent connections"""

    def __init__(self):
        # Unified per-agent contexts
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

    def _load_remote_contexts(self, config_dir: str = None) -> None:
        """Load remote agent contexts from JSON config files into _contexts."""
        if config_dir is None:
            # Default to python/configs/agent_cards relative to current file
            current_file = Path(__file__)
            config_dir = (
                current_file.parent.parent.parent.parent / "configs" / "agent_cards"
            )
        else:
            config_dir = Path(config_dir)

        if not config_dir.exists():
            self._remote_contexts_loaded = True
            return

        for json_file in config_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                agent_name = config_data.get("name")
                if not agent_name:
                    continue

                # Validate required fields
                required_fields = ["name", "url"]
                if not all(field in config_data for field in required_fields):
                    continue

                # Don't overwrite existing context with a constructed one that has more info
                existing = self._contexts.get(agent_name)
                if existing and existing.instance:
                    continue

                url = config_data.get("url")
                self._contexts[agent_name] = AgentContext(name=agent_name, url=url)

            except (json.JSONDecodeError, FileNotFoundError, KeyError):
                continue
        self._remote_contexts_loaded = True

    def _ensure_remote_contexts_loaded(self) -> None:
        if not self._remote_contexts_loaded:
            self._load_remote_contexts()

    async def start_agent(
        self,
        agent_name: str,
        with_listener: bool = True,
        listener_port: int = None,
        listener_host: str = "localhost",
        notification_callback: NotificationCallbackType = None,
    ) -> AgentCard:
        """Start an agent, optionally with a notification listener."""
        # Use agent-specific lock to prevent concurrent starts of the same agent
        agent_lock = self._get_agent_lock(agent_name)
        async with agent_lock:
            ctx = await self._get_or_create_context(agent_name)

            # Record listener preferences on the context
            if with_listener:
                ctx.desired_listener_host = listener_host
                ctx.desired_listener_port = listener_port
                ctx.notification_callback = notification_callback

            # If already set up, return card
            if ctx.agent_card and (ctx.client or ctx.server_task):
                return ctx.agent_card

            # Ensure AgentCard
            await self._ensure_agent_card(ctx)

            # Ensure listener if requested and supported
            if with_listener:
                await self._ensure_listener(ctx)

            # Start local agent service if needed
            if ctx.instance:
                await self._ensure_local_service(ctx)

            # Ensure client connection
            await self._ensure_client(ctx)

            return ctx.agent_card

    async def _ensure_agent_card(self, ctx: AgentContext) -> None:
        """Ensure ctx.agent_card is populated."""
        if ctx.agent_card:
            return
        if ctx.url and not ctx.instance:
            if not ctx.url:
                raise ValueError(f"Remote agent '{ctx.name}' missing URL")
            async with httpx.AsyncClient() as httpx_client:
                try:
                    resolver = A2ACardResolver(
                        httpx_client=httpx_client, base_url=ctx.url
                    )
                    ctx.agent_card = await resolver.get_agent_card()
                    logger.info(f"Loaded agent card: {ctx.name}")
                except Exception as e:
                    logger.error(f"Failed to get agent card for {ctx.name}: {e}")
                    # Proceed without card if remote doesn't expose it
        else:
            if not ctx.instance:
                # Create instance lazily here to source the card
                agent_class = registry.get_agent_class_by_name(ctx.name)
                if not agent_class:
                    raise ValueError(f"Agent '{ctx.name}' not found in registry")
                ctx.instance = agent_class()
                logger.info(f"Created new instance for agent '{ctx.name}'")
            ctx.agent_card = ctx.instance.agent_card

    async def _ensure_listener(self, ctx: AgentContext) -> None:
        """Ensure listener is running if supported by agent card."""
        if ctx.listener_task or not ctx.agent_card:
            return
        if not getattr(ctx.agent_card.capabilities, "push_notifications", False):
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
        url = ctx.url or (ctx.agent_card.url if ctx.agent_card else None)
        if not url:
            raise ValueError(f"Unable to determine URL for agent '{ctx.name}'")
        ctx.client = AgentClient(url, push_notification_url=ctx.listener_url)
        # Log based on whether it's a local service or a remote URL-only connection
        if ctx.instance:
            logger.info(f"Started agent '{ctx.name}' at {url}")
        else:
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

    async def _ensure_local_service(self, ctx: AgentContext):
        """Start the local agent service if not already running."""
        if ctx.server_task:
            return
        if not ctx.instance:
            agent_class = registry.get_agent_class_by_name(ctx.name)
            if not agent_class:
                raise ValueError(f"Agent '{ctx.name}' not found in registry")
            ctx.instance = agent_class()
            logger.info(f"Created new instance for agent '{ctx.name}'")
        server_task = asyncio.create_task(ctx.instance.serve())
        ctx.server_task = server_task
        await asyncio.sleep(0.5)

    async def _get_or_create_context(
        self,
        agent_name: str,
    ) -> AgentContext:
        """Get or initialize an AgentContext for local or remote agents."""
        # Load remote contexts lazily
        self._ensure_remote_contexts_loaded()

        ctx = self._contexts.get(agent_name)
        if ctx:
            return ctx

        # Try local agent from registry
        agent_class = registry.get_agent_class_by_name(agent_name)
        if agent_class:
            instance = agent_class()
            ctx = AgentContext(name=agent_name, instance=instance)
            try:
                ctx.agent_card = instance.agent_card
            except Exception:
                pass
            self._contexts[agent_name] = ctx
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
        # Stop local agent
        if ctx.server_task:
            ctx.server_task.cancel()
            try:
                await ctx.server_task
            except asyncio.CancelledError:
                pass
            ctx.server_task = None
        # Remove context
        del self._contexts[agent_name]

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
        return [name for name, ctx in self._contexts.items() if ctx.server_task]

    def list_available_agents(self) -> List[str]:
        """List all available agents from registry and config cards"""
        # Ensure remote contexts are loaded
        self._ensure_remote_contexts_loaded()
        local_agents = registry.list_agent_names()
        remote_agents = [
            name for name, ctx in self._contexts.items() if ctx.url and not ctx.instance
        ]
        # Deduplicate while preserving order (locals first)
        seen = set()
        merged = []
        for name in local_agents + remote_agents:
            if name not in seen:
                seen.add(name)
                merged.append(name)
        return merged

    async def stop_all(self):
        """Stop all running agents"""
        for agent_name in list(self._contexts.keys()):
            await self.stop_agent(agent_name)

    def get_agent_card(
        self, agent_name: str, fetch_if_missing: bool = False
    ) -> Optional[AgentCard]:
        """Get AgentCard object for any known agent; returns None if not available.

        By default, this does not perform network I/O. If fetch_if_missing is True
        and a URL is available for the agent, this will attempt to fetch the card:
        - If no event loop is running, it will fetch synchronously (blocking).
        - If an event loop is running, it schedules a background fetch and returns
          None immediately (the card will be cached when the task completes).
        """
        self._ensure_remote_contexts_loaded()
        ctx = self._contexts.get(agent_name)
        if not ctx:
            # Try to construct a local context from registry for convenience
            agent_class = registry.get_agent_class_by_name(agent_name)
            if agent_class:
                instance = agent_class()
                ctx = AgentContext(name=agent_name, instance=instance)
                try:
                    ctx.agent_card = instance.agent_card
                except Exception:
                    pass
                self._contexts[agent_name] = ctx
            else:
                return None
        if ctx.agent_card:
            return ctx.agent_card
        if ctx.instance:
            try:
                return ctx.instance.agent_card
            except Exception:
                return None
        # URL-only context without cached card
        if fetch_if_missing and ctx.url:

            async def _fetch_card():
                async with httpx.AsyncClient() as httpx_client:
                    try:
                        resolver = A2ACardResolver(
                            httpx_client=httpx_client, base_url=ctx.url
                        )  # type: ignore[arg-type]
                        card = await resolver.get_agent_card()
                        ctx.agent_card = card
                        logger.info(f"Fetched and cached agent card: {ctx.name}")
                    except Exception as e:
                        logger.error(f"Failed to fetch agent card for {ctx.name}: {e}")

            try:
                loop = asyncio.get_running_loop()
                # Schedule background fetch; caller can retry later
                loop.create_task(_fetch_card())
                return None
            except RuntimeError:
                # No running loop: perform fetch synchronously
                asyncio.run(_fetch_card())
                return ctx.agent_card

        return None


# Global default instance for backward compatibility and ease of use
_default_remote_connections = RemoteConnections()


# Convenience functions that delegate to the default instance
def get_default_remote_connections() -> RemoteConnections:
    """Get the default RemoteConnections instance"""
    return _default_remote_connections
