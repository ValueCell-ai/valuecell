import asyncio
import logging
from typing import Dict, List

from valuecell.core.agent.client import AgentClient
from valuecell.core.agent.registry import AgentRegistry
from valuecell.core.agent.listener import NotificationListener
from valuecell.utils import get_next_available_port

logger = logging.getLogger(__name__)


class RemoteConnections:
    """Manager for remote Agent connections"""

    def __init__(self):
        self._connections: Dict[str, AgentClient] = {}
        self._running_agents: Dict[str, asyncio.Task] = {}
        self._agent_instances: Dict[str, object] = {}
        self._listeners: Dict[str, asyncio.Task] = {}
        self._listener_urls: Dict[str, str] = {}

    async def start_agent(
        self,
        agent_name: str,
        with_listener: bool = True,
        listener_port: int = None,
        listener_host: str = "localhost",
        notification_callback: callable = None,
    ) -> str:
        """Start an agent, optionally with a notification listener."""
        agent_class = AgentRegistry.get_agent(agent_name)
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
        """List all available agents from registry"""
        return AgentRegistry.list_agents()

    async def stop_all(self):
        """Stop all running agents"""
        for agent_name in list(self._running_agents.keys()):
            await self.stop_agent(agent_name)

    def get_agent_info(self, agent_name: str) -> dict:
        """Get agent information including listener info"""
        if agent_name not in self._agent_instances:
            return None

        agent_instance = self._agent_instances[agent_name]
        return {
            "name": agent_name,
            "url": agent_instance.agent_card.url,
            "listener_url": self._listener_urls.get(agent_name),
            "card": agent_instance.agent_card.model_dump(exclude_none=True),
            "running": agent_name in self._running_agents,
            "has_listener": agent_name in self._listeners,
        }
