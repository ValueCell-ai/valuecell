import json
import logging
from pathlib import Path
from typing import Dict, Optional, Type

import httpx
import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
    TaskUpdater,
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from valuecell.core.agent.registry import AgentRegistry
from valuecell.core.agent.types import BaseAgent
from valuecell.utils import (
    get_agent_card_path,
    get_next_available_port,
    parse_host_port,
)

logger = logging.getLogger(__name__)


def serve(
    name: str = None,
    host: str = "localhost",
    port: int = None,
    streaming: bool = True,
    push_notifications: bool = False,
    description: str = None,
    version: str = "1.0.0",
    skills: list[AgentSkill | dict] = None,
    **extra_kwargs,
):
    def decorator(cls: Type) -> Type:
        if extra_kwargs:
            logger.warning(
                f"Extra kwargs {extra_kwargs} are not used in the @serve decorator"
            )

        # Build agent card (port will be assigned when server starts)
        agent_skills = []
        if skills:
            for skill in skills:
                if isinstance(skill, dict):
                    agent_skills.append(AgentSkill(**skill))
                elif isinstance(skill, AgentSkill):
                    agent_skills.append(skill)

        # Determine the agent name consistently
        agent_name = name or cls.__name__

        # Create decorated class
        class DecoratedAgent(cls):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                # Assign port when instance is created
                actual_port = port or get_next_available_port()

                # Create agent card with actual port
                self.agent_card = AgentCard(
                    name=agent_name,
                    description=description
                    or f"No description available for {agent_name}",
                    url=f"http://{host}:{actual_port}/",
                    version=version,
                    default_input_modes=["text"],
                    default_output_modes=["text"],
                    capabilities=AgentCapabilities(
                        streaming=streaming, push_notifications=push_notifications
                    ),
                    skills=agent_skills,
                    supports_authenticated_extended_card=False,
                )

                self._host = host
                self._port = actual_port
                self._executor = None
                self._server_task = None

            async def serve(self):
                # Create AgentExecutor wrapper
                self._executor = _create_agent_executor(self)

                # Setup server components
                client = httpx.AsyncClient()
                push_notification_config_store = InMemoryPushNotificationConfigStore()
                push_notification_sender = BasePushNotificationSender(
                    client, config_store=push_notification_config_store
                )
                request_handler = DefaultRequestHandler(
                    agent_executor=self._executor,
                    task_store=InMemoryTaskStore(),
                    push_config_store=push_notification_config_store,
                    push_sender=push_notification_sender,
                )

                server_app = A2AStarletteApplication(
                    agent_card=self.agent_card,
                    http_handler=request_handler,
                )

                # Start server
                config = uvicorn.Config(
                    server_app.build(),
                    host=self._host,
                    port=self._port,
                    log_level="info",
                )
                server = uvicorn.Server(config)
                logger.info(f"Starting {agent_name} server at {self.agent_card.url}")
                await server.serve()

        # Preserve original class metadata
        DecoratedAgent.__name__ = cls.__name__
        DecoratedAgent.__qualname__ = cls.__qualname__

        # Store agent name as class attribute for registry management
        DecoratedAgent.__agent_name__ = agent_name

        # Register to registry
        try:
            AgentRegistry.register(DecoratedAgent, agent_name)
        except ImportError:
            # Registry not available, skip registration
            logger.warning(
                f"Agent registry not available, skipping registration for {DecoratedAgent.__name__}"
            )

        return DecoratedAgent

    return decorator


class GenericAgentExecutor(AgentExecutor):
    def __init__(self, agent: BaseAgent):
        self.agent = agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Ensure agent implements streaming interface
        if not hasattr(self.agent, "stream"):
            raise NotImplementedError(
                f"Agent {self.agent.__class__.__name__} must implement 'stream' method"
            )

        # Prepare query and ensure a task exists in the system
        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        # Helper state
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        artifact_id = f"{self.agent.__class__.__name__}-artifact"
        chunk_idx = 0

        # Local helper to add a chunk
        async def _add_chunk(content: str, last: bool = False):
            nonlocal chunk_idx
            parts = [Part(root=TextPart(text=content))]
            await updater.add_artifact(
                parts=parts,
                artifact_id=artifact_id,
                append=chunk_idx > 0,
                last_chunk=last,
            )
            if not last:
                chunk_idx += 1

        # Stream from the user agent and update task incrementally
        try:
            async for item in self.agent.stream(query, task.context_id, task.id):
                content = item.get("content", "")
                is_complete = item.get("is_task_complete", True)

                await updater.update_status(TaskState.working)
                await _add_chunk(content, last=is_complete)

                if is_complete:
                    await updater.complete()
                    break
        except Exception as e:
            message = (
                f"Error during {self.agent.__class__.__name__} agent execution : {e}"
            )
            logger.error(message)
            await updater.update_status(
                TaskState.failed,
                message=new_agent_text_message(message, task.context_id, task.id),
                final=True,
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Default cancel operation
        raise ServerError(error=UnsupportedOperationError())


def _create_agent_executor(agent_instance):
    return GenericAgentExecutor(agent_instance)


def _get_serve_params_by_agent_name(name: str) -> Optional[Dict]:
    """
    Reads JSON files from agent_cards directory and returns the first one where name matches.

    Args:
        name: The agent name to search for

    Returns:
        Dict: The agent configuration dictionary if found, None otherwise
    """
    agent_cards_path = Path(get_agent_card_path())

    # Check if the agent_cards directory exists
    if not agent_cards_path.exists():
        return None

    # Iterate through all JSON files in the agent_cards directory
    for json_file in agent_cards_path.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                agent_config = json.load(f)

            # Check if this agent config has the matching name
            if not isinstance(agent_config, dict):
                continue
            if agent_config.get("name") != name:
                continue
            if "url" in agent_config and agent_config["url"]:
                host, port = parse_host_port(
                    agent_config.get("url"), default_scheme="http"
                )
                agent_config["host"] = host
                agent_config["port"] = port

            return agent_config

        except (json.JSONDecodeError, IOError):
            # Skip files that can't be read or parsed
            continue

    # Return None if no matching agent is found
    return None


def create_wrapped_agent(agent_class: Type[BaseAgent]):
    # Get agent configuration from agent cards
    agent_config = _get_serve_params_by_agent_name(agent_class.__name__)
    if not agent_config:
        raise ValueError(
            f"No agent configuration found for {agent_class.__name__} in agent cards"
        )

    return serve(**agent_config)(agent_class)()
