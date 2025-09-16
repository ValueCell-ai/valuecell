import logging
from typing import AsyncGenerator

from a2a.types import TaskArtifactUpdateEvent, TaskState, TaskStatusUpdateEvent
from valuecell.core.agent.connect import get_default_remote_connections
from valuecell.core.session import Role, get_default_session_manager
from valuecell.core.task import TaskManager
from valuecell.core.types import (
    MessageChunk,
    MessageChunkMetadata,
    MessageDataKind,
    UserInput,
)

from .callback import store_task_in_session
from .models import ExecutionPlan
from .planner import ExecutionPlanner

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self):
        self.session_manager = get_default_session_manager()
        self.task_manager = TaskManager()
        self.agent_connections = get_default_remote_connections()

        self.planner = ExecutionPlanner(self.agent_connections)

    async def process_user_input(
        self, user_input: UserInput
    ) -> AsyncGenerator[MessageChunk, None]:
        """Main entry point for processing user input - streams results"""

        session_id = user_input.meta.session_id
        # Add user message to session
        await self.session_manager.add_message(session_id, Role.USER, user_input.query)

        try:
            # Create execution plan with user_id
            plan = await self.planner.create_plan(user_input)

            # Stream execution results
            full_response = ""
            async for chunk in self._execute_plan(plan, user_input.meta.model_dump()):
                full_response += chunk.content
                yield chunk

            # Add final assistant response to session
            await self.session_manager.add_message(
                session_id, Role.AGENT, full_response
            )

        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            await self.session_manager.add_message(session_id, Role.SYSTEM, error_msg)
            yield MessageChunk(
                content=f"(Error): {error_msg}",
                kind=MessageDataKind.TEXT,
                meta=MessageChunkMetadata(
                    session_id=session_id, user_id=user_input.meta.user_id
                ),
                is_final=True,
            )

    async def _execute_plan(
        self, plan: ExecutionPlan, metadata: dict
    ) -> AsyncGenerator[MessageChunk, None]:
        """Execute an execution plan - streams results"""

        session_id, user_id = metadata["session_id"], metadata["user_id"]
        if not plan.tasks:
            yield MessageChunk(
                content="No tasks found for this request.",
                kind=MessageDataKind.TEXT,
                meta=MessageChunkMetadata(session_id=session_id, user_id=user_id),
                is_final=True,
            )
            return

        # Execute tasks (simple sequential execution for now)
        for task in plan.tasks:
            try:
                # Register the task with TaskManager
                await self.task_manager.store.save_task(task)

                # Stream task execution results with user_id context
                async for chunk in self._execute_task(task, plan.query, metadata):
                    yield chunk

            except Exception as e:
                error_msg = f"Error executing {task.agent_name}: {str(e)}"
                yield MessageChunk(
                    content=f"(Error): {error_msg}",
                    kind=MessageDataKind.TEXT,
                    meta=MessageChunkMetadata(session_id=session_id, user_id=user_id),
                    is_final=True,
                )

        # Check if no results were produced
        if not plan.tasks:
            yield MessageChunk(
                content="No agents were able to process this request.",
                kind=MessageDataKind.TEXT,
                meta=MessageChunkMetadata(session_id=session_id, user_id=user_id),
                is_final=True,
            )

    async def _execute_task(
        self, task, query: str, metadata: dict
    ) -> AsyncGenerator[MessageChunk, None]:
        """Execute a single task by calling the specified agent - streams results"""

        try:
            # Start task
            await self.task_manager.start_task(task.task_id)

            # Get agent client
            agent_card = await self.agent_connections.start_agent(
                task.agent_name, notification_callback=store_task_in_session
            )
            client = await self.agent_connections.get_client(task.agent_name)
            if not client:
                raise RuntimeError(f"Could not connect to agent {task.agent_name}")

            streaming = agent_card.capabilities.streaming
            response = await client.send_message(
                query,
                context_id=task.session_id,
                metadata=metadata,
                streaming=streaming,
            )

            # Process streaming responses
            remote_task, event = await anext(response)
            if remote_task.status.state == TaskState.submitted:
                task.remote_task_ids.append(remote_task.id)
            if not streaming:
                return

            async for remote_task, event in response:
                if (
                    isinstance(event, TaskStatusUpdateEvent)
                    # and event.status.state == TaskState.input_required
                ):
                    logger.info(f"Task status update: {event.status.state}")
                    continue
                if isinstance(event, TaskArtifactUpdateEvent):
                    yield MessageChunk(
                        content=event.artifact.parts[0].root.text,
                        kind=MessageDataKind.TEXT,
                        meta=MessageChunkMetadata(
                            session_id=task.session_id, user_id=task.user_id
                        ),
                    )

            # Complete task
            await self.task_manager.complete_task(task.task_id)

        except Exception as e:
            # Fail task
            await self.task_manager.fail_task(task.task_id, str(e))
            raise e

    async def create_session(self, user_id: str, title: str = None):
        """Create a new session for the user"""
        return await self.session_manager.create_session(user_id, title)

    async def close_session(self, session_id: str):
        """Close an existing session"""
        # In a more sophisticated implementation, you might want to:
        # 1. Cancel any ongoing tasks in this session
        # 2. Save session metadata
        # 3. Clean up resources

        # Cancel any running tasks for this session
        cancelled_count = await self.task_manager.cancel_session_tasks(session_id)

        # Add a system message to mark the session as closed
        await self.session_manager.add_message(
            session_id,
            Role.SYSTEM,
            f"Session closed. {cancelled_count} tasks were cancelled.",
        )

    async def get_session_history(self, session_id: str):
        """Get session message history"""
        return await self.session_manager.get_session_messages(session_id)

    async def get_user_sessions(self, user_id: str, limit: int = 100, offset: int = 0):
        """Get all sessions for a user"""
        return await self.session_manager.list_user_sessions(user_id, limit, offset)

    async def cleanup(self):
        """Cleanup resources"""
        await self.agent_connections.stop_all()


_orchestrator = AgentOrchestrator()


def get_default_orchestrator() -> AgentOrchestrator:
    return _orchestrator
