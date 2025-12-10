"""
Agent stream service for handling streaming agent interactions.
"""

import asyncio
from typing import AsyncGenerator, Optional

from loguru import logger

from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.task.executor import TaskExecutor
from valuecell.core.task.locator import get_task_service
from valuecell.core.task.models import TaskPattern, TaskStatus
from valuecell.core.types import UserInput, UserInputMetadata
from valuecell.utils.uuid import generate_conversation_id

_TASK_AUTORESTART_STARTED = False
_AGENT_CLASSES_PRELOADED = False


def _preload_agent_classes_once() -> None:
    """Preload local agent classes once to avoid Windows import lock deadlocks.

    This must run in the main thread before any async operations that might
    trigger imports in worker threads. Safe to call multiple times.
    """
    global _AGENT_CLASSES_PRELOADED
    if _AGENT_CLASSES_PRELOADED:
        return
    _AGENT_CLASSES_PRELOADED = True

    try:
        logger.info("Preloading local agent classes...")
        rc = RemoteConnections()
        rc.preload_local_agent_classes(
            names=["GridStrategyAgent", "PromptBasedStrategyAgent"]
        )
        logger.info("✓ Local agent classes preloaded")
    except Exception as e:
        logger.warning(f"✗ Failed to preload local agent classes: {e}")


class AgentStreamService:
    """Service for handling streaming agent queries."""

    def __init__(self):
        """Initialize the agent stream service."""
        # Preload agent classes before creating orchestrator to avoid
        # Windows import lock deadlocks when using thread pools
        _preload_agent_classes_once()

        self.orchestrator = AgentOrchestrator()
        logger.info("Agent stream service initialized")

    async def stream_query_agent(
        self,
        query: str,
        agent_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream agent responses for a given query.

        Args:
            query: User query to process
            agent_name: Optional specific agent name to use. If provided, takes precedence over query parsing.
            conversation_id: Optional conversation ID for context tracking.

        Yields:
            str: Content chunks from the agent response
        """
        try:
            logger.info(f"Processing streaming query: {query[:100]}...")

            user_id = "default_user"
            target_agent_name = agent_name

            conversation_id = conversation_id or generate_conversation_id()

            user_input_meta = UserInputMetadata(
                user_id=user_id, conversation_id=conversation_id
            )

            user_input = UserInput(
                query=query, target_agent_name=target_agent_name, meta=user_input_meta
            )

            # Use the orchestrator's process_user_input method for streaming
            async for response_chunk in self.orchestrator.process_user_input(
                user_input
            ):
                yield response_chunk.model_dump(exclude_none=True)

        except Exception as e:
            logger.error(f"Error in stream_query_agent: {str(e)}")
            yield f"Error processing query: {str(e)}"


async def _auto_resume_recurring_tasks(agent_service: AgentStreamService) -> None:
    """Resume persisted recurring tasks that were running before shutdown."""
    global _TASK_AUTORESTART_STARTED
    if _TASK_AUTORESTART_STARTED:
        return
    _TASK_AUTORESTART_STARTED = True

    task_service = get_task_service()
    try:
        running_tasks = await task_service.list_tasks(status=TaskStatus.RUNNING)
    except Exception:
        logger.exception("Task auto-resume: failed to load tasks from store")
        return

    candidates = [
        task for task in running_tasks if task.pattern == TaskPattern.RECURRING
    ]
    if not candidates:
        logger.info("Task auto-resume: no recurring running tasks found")
        return

    executor = agent_service.orchestrator.task_executor

    task_service = get_task_service()
    for task in candidates:
        try:
            # Reset to pending and persist so TaskExecutor sees the correct state
            task.status = TaskStatus.PENDING
            await task_service.update_task(task)

            thread_id = task.thread_id or task.task_id
            asyncio.create_task(
                _drain_execute_task(executor, task, thread_id, task_service)
            )
            logger.info(
                "Task auto-resume: scheduled recurring task {} for execution",
                task.task_id,
            )
        except Exception:
            logger.exception(
                "Task auto-resume: failed to schedule task {}", task.task_id
            )


async def _drain_execute_task(
    executor: TaskExecutor, task, thread_id: str, task_service
) -> None:
    """Execute a single task via TaskExecutor and discard produced responses."""
    try:
        async for _ in executor.execute_task(task, thread_id=thread_id, resumed=True):
            pass
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Task auto-resume: execution failed for task {}", task.task_id)
