import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List

import httpx
from a2a.client import A2ACardResolver
from a2a.types import AgentCard
from valuecell.core.agent.client import AgentClient
from valuecell.core.agent.listener import NotificationListener
from valuecell.core.agent import registry
from valuecell.utils import get_agent_card_path, get_next_available_port

logger = logging.getLogger(__name__)


class RemoteConnections:
    """Manager for remote Agent connections"""

    def __init__(self):
        self._connections: Dict[str, AgentClient] = {}
        self._running_agents: Dict[str, asyncio.Task] = {}
        self._agent_instances: Dict[str, object] = {}
        self._listeners: Dict[str, asyncio.Task] = {}
        self._listener_urls: Dict[str, str] = {}
        # Remote agent cards loaded from config files
        self._remote_agent_cards: Dict[str, AgentCard] = {}
        # Remote agent configs (JSON data from config files)
        self._remote_agent_configs: Dict[str, dict] = {}

    def _load_remote_agent_configs(self, config_dir: str = None) -> None:
        """Load remote agent configs from JSON files (sync operation)."""
        if config_dir is None:
            # Default to python/configs/agent_cards relative to current file
            current_file = Path(__file__)
            config_dir = (
                current_file.parent.parent.parent.parent / "configs" / "agent_cards"
            )
        else:
            config_dir = Path(config_dir)

        if not config_dir.exists():
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

                self._remote_agent_configs[agent_name] = config_data

            except (json.JSONDecodeError, FileNotFoundError, KeyError):
                continue

    async def load_remote_agents(self, config_dir: str = None) -> None:
        """Load remote agent cards from configuration directory."""
        if config_dir is None:
            config_dir = get_agent_card_path()
        else:
            config_dir = Path(config_dir)

        if not config_dir.exists():
            logger.warning(f"Remote agent config directory not found: {config_dir}")
            return

        async with httpx.AsyncClient() as httpx_client:
            loaded_count = 0
            for json_file in config_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        card_data = json.load(f)

                    agent_name = card_data.get("name")
                    if not agent_name:
                        logger.warning(f"No 'name' field in {json_file}, skipping")
                        continue

                    # Validate required fields
                    required_fields = ["name", "url"]
                    if not all(field in card_data for field in required_fields):
                        logger.warning(
                            f"Missing required fields in {json_file}, skipping"
                        )
                        continue

                    resolver = A2ACardResolver(
                        httpx_client=httpx_client, base_url=card_data["url"]
                    )
                    self._remote_agent_cards[
                        agent_name
                    ] = await resolver.get_agent_card()
                    loaded_count += 1
                    logger.info(
                        f"Loaded remote agent card: {agent_name} from {json_file.name}"
                    )

                except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                    logger.error(
                        f"Failed to load remote agent card from {json_file}: {e}"
                    )

        logger.info(f"Loaded {loaded_count} remote agent cards from {config_dir}")

    async def connect_remote_agent(self, agent_name: str) -> str:
        """Connect to a remote agent (no lifecycle management)."""
        if agent_name not in self._remote_agent_configs:
            # Auto-load configs if not found
            self._load_remote_agent_configs()

        if agent_name not in self._remote_agent_configs:
            raise ValueError(f"Remote agent '{agent_name}' not found in loaded cards")

        config_data = self._remote_agent_configs[agent_name]
        agent_url = config_data["url"]

        # Create client connection for remote agent
        self._connections[agent_name] = AgentClient(agent_url)

        logger.info(f"Connected to remote agent '{agent_name}' at {agent_url}")
        return agent_url

    async def start_agent(
        self,
        agent_name: str,
        with_listener: bool = True,
        listener_port: int = None,
        listener_host: str = "localhost",
        notification_callback: callable = None,
    ) -> str:
        """Start an agent, optionally with a notification listener."""
        # Check if it's a remote agent first
        if agent_name in self._remote_agent_configs:
            return await self._handle_remote_agent(agent_name)

        # Handle local agent
        agent_class = registry.get_agent_class_by_name(agent_name)
        if not agent_class:
            raise ValueError(f"Agent '{agent_name}' not found in registry")

        # Create Agent instance
        agent_instance = agent_class()
        self._agent_instances[agent_name] = agent_instance

        listener_url = None

        # Start listener if requested and agent supports push notifications
        if with_listener and agent_instance.agent_card.capabilities.push_notifications:
            try:
                listener_url = await self._start_listener_for_agent(
                    agent_name,
                    listener_host=listener_host,
                    listener_port=listener_port,
                    notification_callback=notification_callback,
                )
            except Exception as e:
                logger.error(f"Failed to start listener for '{agent_name}': {e}")
                await self._cleanup_agent(agent_name)
                raise RuntimeError(
                    f"Failed to start listener for '{agent_name}'"
                ) from e

        # Start agent service
        try:
            await self._start_agent_service(agent_name, agent_instance)
        except Exception as e:
            logger.error(f"Failed to start agent '{agent_name}': {e}")
            await self._cleanup_agent(agent_name)
            raise RuntimeError(f"Failed to start agent '{agent_name}'") from e

        # Create client connection with listener URL
        agent_url = agent_instance.agent_card.url
        self._create_client_for_agent(agent_name, agent_instance, listener_url)

        return agent_url

    async def _handle_remote_agent(self, agent_name: str) -> str:
        """Handle remote agent connection and card loading."""
        config_data = self._remote_agent_configs[agent_name]
        agent_url = config_data["url"]

        # Load actual agent card using A2ACardResolver
        async with httpx.AsyncClient() as httpx_client:
            try:
                resolver = A2ACardResolver(
                    httpx_client=httpx_client, base_url=agent_url
                )
                agent_card = await resolver.get_agent_card()
                self._remote_agent_cards[agent_name] = agent_card
                logger.info(f"Loaded agent card for remote agent: {agent_name}")
            except Exception as e:
                logger.error(f"Failed to get agent card for {agent_name}: {e}")
                # Fallback: create basic card from config
                agent_card = None

        # Create client connection
        self._connections[agent_name] = AgentClient(agent_url)
        logger.info(f"Connected to remote agent '{agent_name}' at {agent_url}")

        return agent_url

    async def _start_listener_for_agent(
        self,
        agent_name: str,
        listener_host: str,
        listener_port: int = None,
        notification_callback: callable = None,
    ) -> str:
        """Start a NotificationListener for the agent and return its URL."""
        # Auto-assign port if not specified
        if listener_port is None:
            listener_port = get_next_available_port(5000)

        # Create and start listener
        listener = NotificationListener(
            host=listener_host,
            port=listener_port,
            notification_callback=notification_callback,
        )

        listener_task = asyncio.create_task(listener.start_async())
        self._listeners[agent_name] = listener_task

        listener_url = f"http://{listener_host}:{listener_port}/notify"
        self._listener_urls[agent_name] = listener_url

        # Wait a moment for listener to start
        await asyncio.sleep(0.3)
        logger.info(f"Started listener for '{agent_name}' at {listener_url}")

        return listener_url

    async def _start_agent_service(self, agent_name: str, agent_instance: object):
        """Start the agent service (serve) and track the running task."""
        server_task = asyncio.create_task(agent_instance.serve())
        self._running_agents[agent_name] = server_task

        # Wait for agent to start
        await asyncio.sleep(0.5)

    def _create_client_for_agent(
        self, agent_name: str, agent_instance: object, listener_url: str = None
    ):
        """Create an AgentClient for the agent and record the connection."""
        agent_url = agent_instance.agent_card.url
        self._connections[agent_name] = AgentClient(
            agent_url, push_notification_url=listener_url
        )

        logger.info(f"Started agent '{agent_name}' at {agent_url}")
        if listener_url:
            logger.info(f"  └─ with listener at {listener_url}")

    async def _cleanup_agent(self, agent_name: str):
        """Clean up all resources for an agent"""
        # Close client connection
        if agent_name in self._connections:
            await self._connections[agent_name].close()

        # Stop listener
        if agent_name in self._listeners:
            self._listeners[agent_name].cancel()
            try:
                await self._listeners[agent_name]
            except asyncio.CancelledError:
                pass
            del self._listeners[agent_name]

        # Stop agent
        if agent_name in self._running_agents:
            self._running_agents[agent_name].cancel()
            try:
                await self._running_agents[agent_name]
            except asyncio.CancelledError:
                pass
            del self._running_agents[agent_name]

        # Clean up references
        if agent_name in self._connections:
            del self._connections[agent_name]
        if agent_name in self._agent_instances:
            del self._agent_instances[agent_name]
        if agent_name in self._listener_urls:
            del self._listener_urls[agent_name]

    async def get_client(self, agent_name: str) -> AgentClient:
        """Get Agent client connection"""
        if agent_name not in self._connections:
            await self.start_agent(agent_name)

        return self._connections[agent_name]

    async def stop_agent(self, agent_name: str):
        """Stop Agent service and associated listener"""
        await self._cleanup_agent(agent_name)
        logger.info(f"Stopped agent '{agent_name}' and its listener")

    def list_running_agents(self) -> List[str]:
        """List running agents"""
        return list(self._running_agents.keys())

    def list_available_agents(self) -> List[str]:
        """List all available agents from registry and remote cards"""
        # Auto-load remote agent configs if not already loaded
        if not self._remote_agent_configs:
            self._load_remote_agent_configs()

        local_agents = registry.list_agent_names()
        remote_agents = list(self._remote_agent_configs.keys())
        return local_agents + remote_agents

    async def stop_all(self):
        """Stop all running agents"""
        for agent_name in list(self._running_agents.keys()):
            await self.stop_agent(agent_name)

    def get_agent_info(self, agent_name: str) -> dict:
        """Get agent information including listener info"""
        # Check if it's a local agent
        if agent_name in self._agent_instances:
            agent_instance = self._agent_instances[agent_name]
            return {
                "name": agent_name,
                "type": "local",
                "url": agent_instance.agent_card.url,
                "listener_url": self._listener_urls.get(agent_name),
                "card": agent_instance.agent_card.model_dump(exclude_none=True),
                "running": agent_name in self._running_agents,
                "has_listener": agent_name in self._listeners,
            }

        # Check if it's a remote agent
        if agent_name in self._remote_agent_configs:
            config_data = self._remote_agent_configs[agent_name]
            agent_card = self._remote_agent_cards.get(agent_name)
            return {
                "name": agent_name,
                "type": "remote",
                "url": config_data.get("url"),
                "card": (
                    agent_card.model_dump(exclude_none=True)
                    if agent_card
                    else config_data
                ),
                "connected": agent_name in self._connections,
                "running": False,  # Remote agents are not managed by us
                "has_listener": False,
            }

        return None

    def list_remote_agents(self) -> List[str]:
        """List remote agents loaded from config files"""
        # Auto-load remote agent configs if not already loaded
        if not self._remote_agent_configs:
            self._load_remote_agent_configs()
        return list(self._remote_agent_configs.keys())

    def get_remote_agent_card(self, agent_name: str) -> dict:
        """Get remote agent card data"""
        # Return actual AgentCard if available, otherwise config data
        if agent_name in self._remote_agent_cards:
            return self._remote_agent_cards[agent_name]
        return self._remote_agent_configs.get(agent_name)
