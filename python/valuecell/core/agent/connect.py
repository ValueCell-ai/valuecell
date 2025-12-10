import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from a2a.types import AgentCard
from loguru import logger

from valuecell.core.agent.card import parse_local_agent_card_dict
from valuecell.core.agent.client import AgentClient
from valuecell.core.agent.decorator import create_wrapped_agent
from valuecell.core.agent.listener import NotificationListener
from valuecell.core.types import BaseAgent, NotificationCallbackType
from valuecell.utils import get_next_available_port

AGENT_METADATA_CLASS_KEY = "local_agent_class"


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
    metadata: Optional[Dict[str, Any]] = None
    # Listener preferences
    desired_listener_host: Optional[str] = None
    desired_listener_port: Optional[int] = None
    notification_callback: Optional[NotificationCallbackType] = None
    # Local in-process agent runtime
    # - `agent_class_spec`: original "module:Class" spec loaded from JSON
    #    We keep the spec so class resolution can be deferred (and performed
    #    off the event loop) when the agent is actually started.
    # - `agent_instance`: concrete wrapped agent instance (created lazily)
    # - `agent_instance_class`: resolved Python class for the agent, if imported
    # - `agent_task`: asyncio.Task running the agent's HTTP server (if launched)
    agent_class_spec: Optional[str] = None
    agent_instance: Optional[BaseAgent] = None
    agent_instance_class: Optional[Type[BaseAgent]] = None
    agent_task: Optional[asyncio.Task] = None

    def _get_metadata_flag(self, key: str) -> Optional[bool]:
        """Retrieve a boolean-like flag from stored metadata or card."""
        if isinstance(self.metadata, dict) and key in self.metadata:
            return bool(self.metadata[key])

        return None

    @property
    def planner_passthrough(self) -> bool:
        flag = self._get_metadata_flag("planner_passthrough")
        return bool(flag) if flag is not None else False

    @property
    def hidden(self) -> bool:
        flag = self._get_metadata_flag("hidden")
        return bool(flag) if flag is not None else False


_LOCAL_AGENT_CLASS_CACHE: Dict[str, Type[Any]] = {}

# Global thread pool for offloading imports. Using a fixed executor allows
# better control and avoids unbounded thread creation when many imports are
# requested concurrently.
executor = ThreadPoolExecutor(max_workers=4)


def _resolve_local_agent_class_sync(spec: str) -> Optional[Type[Any]]:
    """Synchronous resolver used for fallback and direct calls.

    Keeps the original import behavior but is extracted so it can be invoked
    from a thread pool via `run_in_executor`.
    """
    if not spec:
        return None

    cached = _LOCAL_AGENT_CLASS_CACHE.get(spec)
    if cached is not None:
        logger.debug("_resolve_local_agent_class_sync: cache hit for '{}'", spec)
        return cached

    try:
        module_path, class_name = spec.split(":", 1)
        logger.info(
            "_resolve_local_agent_class_sync: importing module '{}' for class '{}'",
            module_path,
            class_name,
        )
        module = import_module(module_path)
        logger.info("_resolve_local_agent_class_sync: module imported, getting class")
        agent_cls = getattr(module, class_name)
        logger.info("_resolve_local_agent_class_sync: class '{}' resolved", class_name)
    except (ValueError, AttributeError, ImportError) as exc:
        logger.error("Failed to import agent class '{}': {}", spec, exc)
        return None

    _LOCAL_AGENT_CLASS_CACHE[spec] = agent_cls
    return agent_cls


async def _resolve_local_agent_class(spec: str) -> Optional[Type[Any]]:
    """Asynchronously resolve a `module:Class` spec to a Python class.

    The actual import is executed in a thread pool via `loop.run_in_executor`
    to avoid blocking the event loop. Results are cached in
    `_LOCAL_AGENT_CLASS_CACHE` to avoid repeated imports.
    """
    if not spec:
        return None

    # Fast path: cache hit
    cached = _LOCAL_AGENT_CLASS_CACHE.get(spec)
    if cached is not None:
        logger.info("_resolve_local_agent_class: cache hit for '{}'", spec)
        return cached

    logger.info(
        "_resolve_local_agent_class: cache miss for '{}', delegating to executor", spec
    )

    loop = asyncio.get_running_loop()
    # Delegate the synchronous import to the thread pool
    try:
        agent_cls = await loop.run_in_executor(
            executor, _resolve_local_agent_class_sync, spec
        )
    except Exception as exc:
        logger.error(
            "_resolve_local_agent_class: threaded import failed for '{}': {}", spec, exc
        )
        return None

    return agent_cls


async def _build_local_agent(ctx: AgentContext):
    """Asynchronously produce a wrapped local agent instance for the
    given `AgentContext`.

    Behavior:
    - If `agent_instance_class` is already present, use it.
    - Otherwise, if `agent_class_spec` is provided, resolve it off the
      event loop (`asyncio.to_thread`) so imports don't block the loop.
      A timeout is applied to prevent hangs on Windows where import lock
      contention between threads and the event loop can cause deadlocks.
    - If resolution fails or times out, fall back to synchronous import.
    - The actual wrapping call (`create_wrapped_agent`) is performed on
      the event loop; this preserves any asyncio-related initialization
      semantics required by the wrapper (if it needs loop context).
    """

    agent_cls = ctx.agent_instance_class
    if agent_cls is None and ctx.agent_class_spec:
        # Try resolving the import in a worker thread with a timeout.
        # Use the async resolver which delegates to a thread pool. If the
        # operation times out, attempt a direct import in the executor as a
        # final fallback.
        try:
            agent_cls = await asyncio.wait_for(
                _resolve_local_agent_class(ctx.agent_class_spec), timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Threaded import timed out for '{}', falling back to executor sync import",
                ctx.agent_class_spec,
            )
            loop = asyncio.get_running_loop()
            agent_cls = await loop.run_in_executor(
                executor, _resolve_local_agent_class_sync, ctx.agent_class_spec
            )

        ctx.agent_instance_class = agent_cls
        if agent_cls is None:
            logger.warning(
                "Unable to resolve local agent class '{}' for '{}'",
                ctx.agent_class_spec,
                ctx.name,
            )
            return None

    if agent_cls is None:
        # No factory available for this context
        return None

    # `create_wrapped_agent` can perform setup that expects to run in the
    # main thread / event loop context (e.g. uvicorn/async setup). Keep it
    # synchronous here so any asyncio primitives are created correctly.
    return create_wrapped_agent(agent_cls)


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

        logger.info(f"Loading agent cards from {agent_card_dir}")
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
                raw_metadata = agent_card_dict.get("metadata")
                metadata: Dict[str, Any] = (
                    dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
                )
                class_spec = metadata.get(AGENT_METADATA_CLASS_KEY)
                if not isinstance(class_spec, str):
                    class_spec = None
                local_agent_card = parse_local_agent_card_dict(agent_card_dict)
                if not local_agent_card:
                    continue
                self._contexts[agent_name] = AgentContext(
                    name=agent_name,
                    url=local_agent_card.url,
                    local_agent_card=local_agent_card,
                    metadata=metadata or None,
                    agent_class_spec=class_spec,
                )
            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                logger.warning(
                    f"Failed to load agent card from {json_file}; skipping: {e}"
                )
                continue
        logger.info(
            f"Loaded {len(self._contexts)} agent card(s) from {agent_card_dir}: {list(self._contexts.keys())}"
        )
        self._remote_contexts_loaded = True

    def _ensure_remote_contexts_loaded(self) -> None:
        if not self._remote_contexts_loaded:
            self._load_remote_contexts()

    def preload_local_agent_classes(self, names: list[str] | None = None) -> None:
        """Preload all local agent classes synchronously at startup.

        If `names` is provided (a list of agent names), only agents whose
        names appear in the list will be considered for preload; others are
        skipped. This preserves the original behavior when `names` is None.

        This method should be called during application startup (before the
        event loop processes requests) to avoid import deadlocks on Windows.
        Importing Python modules in a worker thread while the main thread holds
        the import lock can cause hangs. By importing everything upfront in
        the main thread, we sidestep this issue entirely.
        """
        self._ensure_remote_contexts_loaded()
        preloaded_count = 0
        for name, ctx in self._contexts.items():
            # If caller passed a filter list, skip contexts not in that list
            if names is not None and name not in names:
                logger.debug(
                    "Skipping preload for '{}': not in provided names list", name
                )
                continue
            if not ctx.agent_class_spec:
                logger.debug("Skipping preload for '{}': no agent_class_spec", name)
                continue
            if ctx.agent_instance_class is not None:
                logger.debug("Skipping preload for '{}': class already loaded", name)
                continue
            logger.info(
                "Preloading agent class for '{}' (spec='{}')",
                name,
                ctx.agent_class_spec,
            )
            cls = _resolve_local_agent_class_sync(ctx.agent_class_spec)
            ctx.agent_instance_class = cls
            if cls is None:
                logger.warning(
                    "Failed to preload agent class '{}' for '{}'",
                    ctx.agent_class_spec,
                    name,
                )
            else:
                preloaded_count += 1
                logger.info(
                    "Successfully preloaded class '{}' for '{}'",
                    cls.__name__,
                    name,
                )
        logger.info(
            "Preload complete: {}/{} agent classes loaded",
            preloaded_count,
            len(self._contexts),
        )

    # Public helper primarily for tests or tooling to load from a custom dir
    def load_from_dir(self, config_dir: str) -> None:
        """Load agent contexts from a specific directory of JSON card files."""
        self._load_remote_contexts(config_dir)

    async def start_agent(
        self,
        agent_name: str,
        with_listener: bool = False,
        listener_port: int | None = None,
        listener_host: str = "localhost",
        notification_callback: NotificationCallbackType = None,
    ) -> Optional[AgentCard]:
        """Connect to an agent URL and optionally start a notification listener.

        Returns the AgentCard if available from local configs; otherwise None.
        """
        # Use agent-specific lock to prevent concurrent starts of the same agent
        agent_lock = self._get_agent_lock(agent_name)
        logger.info(
            f"Request to start agent '{agent_name}' (with_listener={with_listener})"
        )
        async with agent_lock:
            ctx = await self._get_or_create_context(agent_name)

            # Record listener preferences on the context
            if with_listener:
                ctx.desired_listener_host = listener_host
                ctx.desired_listener_port = listener_port
                ctx.notification_callback = notification_callback

            await self._ensure_agent_runtime(ctx)

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
        logger.info(
            f"Initializing client for '{ctx.name}' at {url} (listener_url={ctx.listener_url})"
        )
        tmp_client = AgentClient(url, push_notification_url=ctx.listener_url)
        try:
            await self._initialize_client(tmp_client, ctx)
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

    async def _ensure_agent_runtime(self, ctx: AgentContext) -> None:
        """Launch the agent locally if a factory is available."""
        # Existing running task: keep as is
        if ctx.agent_task and not ctx.agent_task.done():
            return

        # Clean up finished tasks and propagate failures
        if ctx.agent_task and ctx.agent_task.done():
            try:
                ctx.agent_task.result()
            except Exception as exc:
                raise RuntimeError(f"Agent '{ctx.name}' failed during startup") from exc
            finally:
                ctx.agent_task = None
                ctx.agent_instance = None

        if ctx.agent_instance is None:
            agent_instance = await _build_local_agent(ctx)
            if agent_instance is None:
                return
            ctx.agent_instance = agent_instance
            logger.info(f"Launching in-process agent '{ctx.name}'")

        if ctx.agent_task is None:
            logger.info(f"Creating task to run in-process agent '{ctx.name}'")
            ctx.agent_task = asyncio.create_task(ctx.agent_instance.serve())
            # Give the event loop a chance to schedule startup work
            await asyncio.sleep(0)
            if ctx.agent_task.done():
                try:
                    ctx.agent_task.result()
                except Exception as exc:
                    raise RuntimeError(
                        f"Agent '{ctx.name}' failed during startup"
                    ) from exc
                finally:
                    ctx.agent_task = None
                    ctx.agent_instance = None

    async def _initialize_client(self, client: AgentClient, ctx: AgentContext) -> None:
        """Initialize client with retry for local agents."""
        retries = 3 if ctx.agent_task else 1
        delay = 0.2
        logger.info(
            f"_initialize_client: initializing client for '{ctx.name}' (retries={retries})"
        )
        for attempt in range(retries):
            try:
                await client.ensure_initialized()
                logger.info(
                    f"Client initialized for '{ctx.name}' on attempt {attempt + 1}"
                )
                return
            except Exception as exc:
                if attempt >= retries - 1:
                    raise
                logger.debug(
                    "Retrying client initialization for '{}' ({}/{}): {}",
                    ctx.name,
                    attempt + 1,
                    retries,
                    exc,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 1.0)

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
        agent_task = ctx.agent_task
        if agent_task:
            if ctx.agent_instance and hasattr(ctx.agent_instance, "shutdown"):
                try:
                    await ctx.agent_instance.shutdown()
                except Exception as exc:
                    logger.warning(
                        "Error shutting down agent '{}': {}", agent_name, exc
                    )
            try:
                await asyncio.wait_for(agent_task, timeout=5)
            except asyncio.TimeoutError:
                agent_task.cancel()
                try:
                    await agent_task
                except asyncio.CancelledError:
                    pass
            finally:
                ctx.agent_task = None
                ctx.agent_instance = None
        elif ctx.agent_instance is not None:
            ctx.agent_instance = None
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

    def get_planable_agent_cards(self) -> Dict[str, AgentCard]:
        """Return AgentCards that are available for planning workflows."""
        self._ensure_remote_contexts_loaded()
        planable_cards: Dict[str, AgentCard] = {}
        for name, ctx in self._contexts.items():
            if ctx.planner_passthrough or ctx.hidden:
                continue
            card = None
            if ctx.client and ctx.client.agent_card:
                card = ctx.client.agent_card
            elif ctx.local_agent_card:
                card = ctx.local_agent_card
            if card:
                planable_cards[name] = card
        return planable_cards

    def is_planner_passthrough(self, agent_name: str) -> bool:
        """Return True if the named agent is marked as planner passthrough.

        The flag is read from stored metadata associated with the AgentContext.
        """
        self._ensure_remote_contexts_loaded()
        ctx = self._contexts.get(agent_name)
        return bool(getattr(ctx, "planner_passthrough", False)) if ctx else False
