"""
Agent stream router for handling streaming agent queries.
"""

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

# ExecutionPlan is not needed here; we resume individual Task executions
from valuecell.core.task.executor import TaskExecutor
from valuecell.core.task.locator import get_task_service
from valuecell.core.task.models import TaskPattern, TaskStatus
from valuecell.server.api.schemas.agent_stream import AgentStreamRequest
from valuecell.server.services.agent_stream_service import AgentStreamService

_TASK_AUTORESTART_STARTED = False


def create_agent_stream_router() -> APIRouter:
    """Create and configure the agent stream router."""

    router = APIRouter(prefix="/agents", tags=["Agent Stream"])
    agent_service = AgentStreamService()

    @router.on_event("startup")
    async def _startup_resume_recurring_tasks() -> None:
        try:
            await _auto_resume_recurring_tasks(agent_service)
        except Exception:
            logger.exception("Failed to schedule recurring task auto-resume")

    @router.post("/stream")
    async def stream_query_agent(request: AgentStreamRequest):
        """
        Stream agent query responses in real-time.

        This endpoint accepts a user query and returns a streaming response
        with agent-generated content in Server-Sent Events (SSE) format.
        """
        try:

            async def generate_stream():
                """Generate SSE formatted stream chunks."""
                async for chunk in agent_service.stream_query_agent(
                    query=request.query,
                    agent_name=request.agent_name,
                    conversation_id=request.conversation_id,
                ):
                    # Format as SSE (Server-Sent Events)
                    yield f"data: {json.dumps(chunk)}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")

    return router


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
