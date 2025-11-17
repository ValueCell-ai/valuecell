import asyncio
import logging
from typing import Type

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
from a2a.types import AgentCard, TaskState, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from valuecell.core.agent.card import find_local_agent_card_by_agent_name
from valuecell.core.constants import DEPENDENCIES
from valuecell.core.types import (
    BaseAgent,
    CommonResponseEvent,
    NotifyResponse,
    StreamResponse,
)
from valuecell.utils import parse_host_port

from .responses import EventPredicates

logger = logging.getLogger(__name__)


def _serve(agent_card: AgentCard):
    """Create a decorator that wraps an agent class with server capabilities.

    Args:
        agent_card: The agent card containing configuration

    Returns:
        A decorator function that adds serve() method to agent classes
    """

    def decorator(cls: Type) -> Type:
        # Determine the agent name consistently
        agent_name = cls.__name__

        # Create decorated class
        class DecoratedAgent(cls):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                # Create agent card with actual port
                self.agent_card = agent_card

                self._host, self._port = parse_host_port(
                    agent_card.url, default_scheme="http"
                )
                self._executor = None
                self._server: uvicorn.Server | None = None

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
                self._server = uvicorn.Server(config)
                logger.info(f"Starting {agent_name} server at {self.agent_card.url}")
                try:
                    await self._server.serve()
                finally:
                    await client.aclose()
                    self._server = None

            async def shutdown(self) -> None:
                if not self._server:
                    return
                self._server.should_exit = True
                await asyncio.sleep(0)

        # Preserve original class metadata
        DecoratedAgent.__name__ = cls.__name__
        DecoratedAgent.__qualname__ = cls.__qualname__

        # Register to registry
        # try:
        #     registry.register(DecoratedAgent, agent_name)
        # except ImportError:
        #     # Registry not available, skip registration
        #     logger.warning(
        #         f"Agent registry not available, skipping registration for {DecoratedAgent.__name__}"
        #     )

        return DecoratedAgent

    return decorator


class GenericAgentExecutor(AgentExecutor):
    """Generic executor for BaseAgent implementations.

    Handles the execution lifecycle including task creation, streaming responses,
    and error handling for agents that implement the BaseAgent interface.
    """

    def __init__(self, agent: BaseAgent):
        """Initialize the executor with an agent instance.

        Args:
            agent: The agent instance to execute
        """
        self.agent = agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent with the given context and event queue.

        Handles task creation if needed, streams responses from the agent,
        and updates task status throughout execution.

        Args:
            context: The request context containing user input and metadata
            event_queue: Queue for sending events back to the client
        """
        # Prepare query and ensure a task exists in the system
        query = context.get_user_input()
        task = context.current_task
        task_meta = context.message.metadata
        agent_name = self.agent.__class__.__name__
        if not task:
            message = context.message
            task = new_task(message)
            task.metadata = task_meta
            await event_queue.enqueue_event(task)

        # Helper state
        task_id = task.id
        context_id = task.context_id
        updater = TaskUpdater(event_queue, task_id, context_id)

        # Stream from the user agent and update task incrementally
        await updater.update_status(
            TaskState.working,
            message=new_agent_text_message(
                f"Task received by {agent_name}", context_id, task_id
            ),
        )
        try:
            # Extract dependencies from task metadata
            dependencies = task_meta.get(DEPENDENCIES)

            query_handler = (
                self.agent.notify
                if task_meta and task_meta.get("notify")
                else self.agent.stream
            )
            async for response in query_handler(
                query, context_id, task_id, dependencies
            ):
                if not isinstance(response, (StreamResponse, NotifyResponse)):
                    raise ValueError(
                        f"Agent {agent_name} yielded invalid response type: {type(response)}"
                    )

                response_event = response.event
                if EventPredicates.is_task_failed(response_event):
                    raise RuntimeError(
                        f"Agent {agent_name} reported failure: {response.content}"
                    )

                metadata = {"response_event": response_event.value}
                if EventPredicates.is_tool_call(response_event):
                    metadata["tool_call_id"] = response.metadata.get("tool_call_id")
                    metadata["tool_name"] = response.metadata.get("tool_name")
                    metadata["tool_result"] = response.metadata.get("tool_result")
                    await updater.update_status(
                        TaskState.working,
                        message=new_agent_text_message(response.content or ""),
                        metadata=metadata,
                    )
                    continue
                if EventPredicates.is_reasoning(response_event):
                    await updater.update_status(
                        TaskState.working,
                        message=new_agent_text_message(response.content or ""),
                        metadata=metadata,
                    )
                    continue

                if not response.content:
                    continue
                if response_event == CommonResponseEvent.COMPONENT_GENERATOR:
                    metadata["component_type"] = response.metadata.get("component_type")
                    metadata["component_id"] = response.metadata.get("component_id")
                await updater.update_status(
                    TaskState.working,
                    message=new_agent_text_message(response.content or ""),
                    metadata=metadata,
                )

        except Exception as e:
            message = f"Error during {agent_name} agent execution: {e}"
            logger.error(message)
            await updater.update_status(
                TaskState.failed,
                message=new_agent_text_message(message, context_id, task_id),
            )
        finally:
            await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the current agent execution.

        Args:
            context: The request context
            event_queue: Queue for sending events

        Raises:
            ServerError: Always raises as cancel is not supported
        """
        # Default cancel operation
        raise ServerError(error=UnsupportedOperationError())


def _create_agent_executor(agent_instance):
    """Create a GenericAgentExecutor for the given agent instance.

    Args:
        agent_instance: The agent instance to wrap

    Returns:
        GenericAgentExecutor instance
    """
    return GenericAgentExecutor(agent_instance)


def create_wrapped_agent(agent_class: Type[BaseAgent]):
    """Create a wrapped agent instance with server capabilities.

    Loads the agent card from local configuration and wraps the agent class
    with server functionality.

    Args:
        agent_class: The agent class to wrap

    Returns:
        Wrapped agent instance ready to serve

    Raises:
        ValueError: If no agent configuration is found
    """
    # Get agent configuration from agent cards
    agent_card = find_local_agent_card_by_agent_name(agent_class.__name__)
    if not agent_card:
        raise ValueError(
            f"No agent configuration found for {agent_class.__name__} in agent cards"
        )

    return _serve(agent_card)(agent_class)()
