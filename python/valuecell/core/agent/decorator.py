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
from valuecell.core.types import (
    BaseAgent,
    NotifyResponse,
    StreamResponse,
    CommonResponseEvent,
)
from valuecell.utils import parse_host_port
from .responses import EventPredicates

logger = logging.getLogger(__name__)


def _serve(agent_card: AgentCard):
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
    def __init__(self, agent: BaseAgent):
        self.agent = agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Prepare query and ensure a task exists in the system
        query = context.get_user_input()
        task = context.current_task
        task_meta = context.metadata
        agent_name = self.agent.__class__.__name__
        if not task:
            message = context.message
            task = new_task(message)
            task.metadata = task_meta
            await event_queue.enqueue_event(task)

        # Helper state
        task_id = task.id
        session_id = task.context_id
        updater = TaskUpdater(event_queue, task_id, session_id)

        # Stream from the user agent and update task incrementally
        await updater.update_status(
            TaskState.working,
            message=new_agent_text_message(
                f"Task received by {agent_name}", session_id, task_id
            ),
        )
        try:
            query_handler = (
                self.agent.notify if task_meta.get("notify") else self.agent.stream
            )
            async for response in query_handler(query, session_id, task_id):
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
                    metadata["tool_result"] = response.metadata.get("content")
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
                message=new_agent_text_message(message, session_id, task_id),
            )
        finally:
            await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Default cancel operation
        raise ServerError(error=UnsupportedOperationError())


def _create_agent_executor(agent_instance):
    return GenericAgentExecutor(agent_instance)


def create_wrapped_agent(agent_class: Type[BaseAgent]):
    # Get agent configuration from agent cards
    agent_card = find_local_agent_card_by_agent_name(agent_class.__name__)
    if not agent_card:
        raise ValueError(
            f"No agent configuration found for {agent_class.__name__} in agent cards"
        )

    return _serve(agent_card)(agent_class)()
