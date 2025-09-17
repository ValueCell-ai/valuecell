import logging
from typing import AsyncGenerator

from a2a.types import TaskArtifactUpdateEvent, TaskState, TaskStatusUpdateEvent
from a2a.utils import get_message_text
from valuecell.core.agent.connect import get_default_remote_connections
from valuecell.core.session import Role, get_default_session_manager
from valuecell.core.task import get_default_task_manager
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
        self.task_manager = get_default_task_manager()
        self.agent_connections = get_default_remote_connections()

        self.planner = ExecutionPlanner(self.agent_connections)

    def _create_message_chunk(
        self,
        content: str,
        session_id: str,
        user_id: str,
        kind: MessageDataKind = MessageDataKind.TEXT,
        is_final: bool = False,
    ) -> MessageChunk:
        """Create a MessageChunk with common metadata"""
        return MessageChunk(
            content=content,
            kind=kind,
            meta=MessageChunkMetadata(session_id=session_id, user_id=user_id),
            is_final=is_final,
        )

    def _create_error_message_chunk(
        self, error_msg: str, session_id: str, user_id: str
    ) -> MessageChunk:
        """Create an error MessageChunk with standardized format"""
        return self._create_message_chunk(
            content=f"(Error): {error_msg}",
            session_id=session_id,
            user_id=user_id,
            is_final=True,
        )

    async def process_user_input(
        self, user_input: UserInput
    ) -> AsyncGenerator[MessageChunk, None]:
        """Main entry point for processing user input - streams results"""

        session_id = user_input.meta.session_id
        # Add user message to session
        if not await self.session_manager.session_exists(session_id):
            await self.session_manager.create_session(
                user_input.meta.user_id, session_id=session_id
            )
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
            yield self._create_error_message_chunk(
                error_msg, session_id, user_input.meta.user_id
            )

    async def _execute_plan(
        self, plan: ExecutionPlan, metadata: dict
    ) -> AsyncGenerator[MessageChunk, None]:
        """Execute an execution plan - streams results"""

        session_id, user_id = metadata["session_id"], metadata["user_id"]
        if not plan.tasks:
            yield self._create_message_chunk(
                "No tasks found for this request.", session_id, user_id, is_final=True
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
                yield self._create_error_message_chunk(error_msg, session_id, user_id)

        # Check if no results were produced
        if not plan.tasks:
            yield self._create_message_chunk(
                "No agents were able to process this request.",
                session_id,
                user_id,
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
                task.agent_name,
                with_listener=False,
                notification_callback=store_task_in_session,
            )
            client = await self.agent_connections.get_client(task.agent_name)
            if not client:
                raise RuntimeError(f"Could not connect to agent {task.agent_name}")

            response = await client.send_message(
                query,
                context_id=task.session_id,
                metadata=metadata,
                streaming=agent_card.capabilities.streaming,
            )

            # Process streaming responses
            async for remote_task, event in response:
                if event is None and remote_task.status.state == TaskState.submitted:
                    task.remote_task_ids.append(remote_task.id)
                    continue

                if (
                    isinstance(event, TaskStatusUpdateEvent)
                    # and event.status.state == TaskState.input_required
                ):
                    logger.info(f"Task status update: {event.status.state}")
                    if event.status.state == TaskState.failed:
                        err_msg = get_message_text(event.status.message)
                        await self.task_manager.fail_task(task.task_id, err_msg)
                        yield self._create_message_chunk(
                            err_msg,
                            task.session_id,
                            task.user_id,
                            is_final=True,
                        )
                        return

                    continue
                if isinstance(event, TaskArtifactUpdateEvent):
                    yield self._create_message_chunk(
                        get_message_text(event.artifact, ""),
                        task.session_id,
                        task.user_id,
                    )

            # Complete task
            await self.task_manager.complete_task(task.task_id)
            yield self._create_message_chunk(
                "", task.session_id, task.user_id, is_final=True
            )

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
