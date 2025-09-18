import asyncio
import logging
from collections import defaultdict
from typing import AsyncGenerator, Dict, Optional

from a2a.types import TaskArtifactUpdateEvent, TaskState, TaskStatusUpdateEvent
from a2a.utils import get_message_text
from valuecell.core.agent.connect import get_default_remote_connections
from valuecell.core.session import Role, SessionStatus, get_default_session_manager
from valuecell.core.task import Task, get_default_task_manager
from valuecell.core.task.models import TaskPattern
from valuecell.core.types import (
    MessageChunk,
    MessageChunkMetadata,
    MessageChunkStatus,
    MessageDataKind,
    UserInput,
)

from .callback import store_task_in_session
from .models import ExecutionPlan
from .planner import ExecutionPlanner, UserInputRequest

logger = logging.getLogger(__name__)

# Constants for configuration
DEFAULT_CONTEXT_TIMEOUT_SECONDS = 3600  # 1 hour
ASYNC_SLEEP_INTERVAL = 0.1  # 100ms


class ExecutionContext:
    """Manages the state of an interrupted execution for resumption"""

    def __init__(self, stage: str, session_id: str, user_id: str):
        self.stage = stage
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = asyncio.get_event_loop().time()
        self.metadata: Dict = {}

    def is_expired(
        self, max_age_seconds: int = DEFAULT_CONTEXT_TIMEOUT_SECONDS
    ) -> bool:
        """Check if this context has expired"""
        current_time = asyncio.get_event_loop().time()
        return current_time - self.created_at > max_age_seconds

    def validate_user(self, user_id: str) -> bool:
        """Validate that the user ID matches the original request"""
        return self.user_id == user_id

    def add_metadata(self, **kwargs):
        """Add metadata to the context"""
        self.metadata.update(kwargs)

    def get_metadata(self, key: str, default=None):
        """Get metadata value"""
        return self.metadata.get(key, default)


class UserInputManager:
    """Manages pending user input requests and their lifecycle"""

    def __init__(self):
        self._pending_requests: Dict[str, UserInputRequest] = {}

    def add_request(self, session_id: str, request: UserInputRequest):
        """Add a pending user input request"""
        self._pending_requests[session_id] = request

    def has_pending_request(self, session_id: str) -> bool:
        """Check if there's a pending request for the session"""
        return session_id in self._pending_requests

    def get_request_prompt(self, session_id: str) -> Optional[str]:
        """Get the prompt for a pending request"""
        request = self._pending_requests.get(session_id)
        return request.prompt if request else None

    def provide_response(self, session_id: str, response: str) -> bool:
        """Provide a response to a pending request"""
        if session_id not in self._pending_requests:
            return False

        request = self._pending_requests[session_id]
        request.provide_response(response)
        del self._pending_requests[session_id]
        return True

    def clear_request(self, session_id: str):
        """Clear a pending request"""
        self._pending_requests.pop(session_id, None)


class AgentOrchestrator:
    """
    Orchestrates execution of user requests through multiple agents with Human-in-the-Loop support.

    This class manages the entire lifecycle of user requests including:
    - Planning phase with user input collection
    - Task execution with interruption support
    - Session state management
    - Error handling and recovery
    """

    def __init__(self):
        self.session_manager = get_default_session_manager()
        self.task_manager = get_default_task_manager()
        self.agent_connections = get_default_remote_connections()

        # Initialize user input management
        self.user_input_manager = UserInputManager()

        # Initialize execution context management
        self._execution_contexts: Dict[str, ExecutionContext] = {}

        # Initialize planner
        self.planner = ExecutionPlanner(self.agent_connections)

    # ==================== Public API Methods ====================

    async def process_user_input(
        self, user_input: UserInput
    ) -> AsyncGenerator[MessageChunk, None]:
        """
        Main entry point for processing user requests with Human-in-the-Loop support.

        Handles three types of scenarios:
        1. New user requests - starts planning and execution
        2. Continuation of interrupted sessions - resumes from saved state
        3. User input responses - provides input to waiting requests

        Args:
            user_input: The user's input containing query and metadata

        Yields:
            MessageChunk: Streaming response chunks from agents
        """
        session_id = user_input.meta.session_id
        user_id = user_input.meta.user_id

        try:
            # Ensure session exists
            session = await self._ensure_session_exists(session_id, user_id)

            # Handle session continuation vs new request
            if session.status == SessionStatus.REQUIRE_USER_INPUT:
                async for chunk in self._handle_session_continuation(user_input):
                    yield chunk
            else:
                async for chunk in self._handle_new_request(user_input):
                    yield chunk

        except Exception as e:
            logger.exception(f"Error processing user input for session {session_id}")
            yield self._create_error_message_chunk(
                f"Error processing request: {str(e)}", session_id, user_id, "__system__"
            )

    async def provide_user_input(self, session_id: str, response: str):
        """
        Provide user input response for a specific session.

        Args:
            session_id: The session ID waiting for input
            response: The user's response to the input request
        """
        if self.user_input_manager.provide_response(session_id, response):
            # Update session status to active
            session = await self.session_manager.get_session(session_id)
            if session:
                session.activate()
                await self.session_manager.update_session(session)

    def has_pending_user_input(self, session_id: str) -> bool:
        """Check if a session has pending user input request"""
        return self.user_input_manager.has_pending_request(session_id)

    def get_user_input_prompt(self, session_id: str) -> Optional[str]:
        """Get the user input prompt for a specific session"""
        return self.user_input_manager.get_request_prompt(session_id)

    async def create_session(self, user_id: str, title: str = None):
        """Create a new session for the user"""
        return await self.session_manager.create_session(user_id, title)

    async def close_session(self, session_id: str):
        """Close an existing session and clean up resources"""
        # Cancel any running tasks for this session
        cancelled_count = await self.task_manager.cancel_session_tasks(session_id)

        # Clean up execution context
        await self._cancel_execution(session_id)

        # Add system message to mark session as closed
        await self.session_manager.add_message(
            session_id,
            Role.SYSTEM,
            f"Session closed. {cancelled_count} tasks were cancelled.",
            agent_name="orchestrator",
        )

    async def get_session_history(self, session_id: str):
        """Get session message history"""
        return await self.session_manager.get_session_messages(session_id)

    async def get_user_sessions(self, user_id: str, limit: int = 100, offset: int = 0):
        """Get all sessions for a user"""
        return await self.session_manager.list_user_sessions(user_id, limit, offset)

    async def cleanup(self):
        """Cleanup resources and expired contexts"""
        await self._cleanup_expired_contexts()
        await self.agent_connections.stop_all()

    # ==================== Private Helper Methods ====================

    # ==================== Private Helper Methods ====================

    async def _handle_user_input_request(self, request: UserInputRequest):
        """Handle user input request from planner"""
        # Extract session_id from request context
        session_id = getattr(request, "session_id", None)
        if session_id:
            self.user_input_manager.add_request(session_id, request)

    async def _ensure_session_exists(self, session_id: str, user_id: str):
        """Ensure a session exists, creating it if necessary"""
        session = await self.session_manager.get_session(session_id)
        if not session:
            await self.session_manager.create_session(user_id, session_id=session_id)
            session = await self.session_manager.get_session(session_id)
        return session

    async def _handle_session_continuation(
        self, user_input: UserInput
    ) -> AsyncGenerator[MessageChunk, None]:
        """Handle continuation of an interrupted session"""
        session_id = user_input.meta.session_id
        user_id = user_input.meta.user_id

        # Validate execution context exists
        if session_id not in self._execution_contexts:
            yield self._create_error_message_chunk(
                "No execution context found for this session. The session may have expired.",
                session_id,
                user_id,
                "__system__",
            )
            return

        context = self._execution_contexts[session_id]

        # Validate context integrity and user consistency
        if not self._validate_execution_context(context, user_id):
            yield self._create_error_message_chunk(
                "Invalid execution context or user mismatch.",
                session_id,
                user_id,
                "__system__",
            )
            await self._cancel_execution(session_id)
            return

        # Provide user response and resume execution
        # If we are in an execution stage, store the pending response for resume
        context.add_metadata(pending_response=user_input.query)
        await self.provide_user_input(session_id, user_input.query)

        # Resume based on execution stage
        if context.stage == "planning":
            async for chunk in self._continue_planning(session_id, context):
                yield chunk
        # TODO: Add support for resuming execution stage if needed
        else:
            yield self._create_error_message_chunk(
                "Resuming execution stage is not yet supported.",
                session_id,
                user_id,
                "__system__",
            )

    async def _handle_new_request(
        self, user_input: UserInput
    ) -> AsyncGenerator[MessageChunk, None]:
        """Handle a new user request"""
        session_id = user_input.meta.session_id

        # Add user message to session
        await self.session_manager.add_message(
            session_id, Role.USER, user_input.query, user_id=user_input.meta.user_id
        )

        # Create planning task with user input callback
        context_aware_callback = self._create_context_aware_callback(session_id)

        planning_task = asyncio.create_task(
            self.planner.create_plan(user_input, context_aware_callback)
        )

        # Monitor planning progress
        async for chunk in self._monitor_planning_task(
            planning_task, user_input, context_aware_callback
        ):
            yield chunk

    def _create_context_aware_callback(self, session_id: str):
        """Create a callback that adds session context to user input requests"""

        async def context_aware_handle(request):
            request.session_id = session_id
            await self._handle_user_input_request(request)

        return context_aware_handle

    async def _monitor_planning_task(
        self, planning_task, user_input: UserInput, callback
    ) -> AsyncGenerator[MessageChunk, None]:
        """Monitor planning task and handle user input interruptions"""
        session_id = user_input.meta.session_id
        user_id = user_input.meta.user_id

        # Wait for planning completion or user input request
        while not planning_task.done():
            if self.has_pending_user_input(session_id):
                # Save planning context
                context = ExecutionContext("planning", session_id, user_id)
                context.add_metadata(
                    original_user_input=user_input,
                    planning_task=planning_task,
                    planner_callback=callback,
                )
                self._execution_contexts[session_id] = context

                # Update session status and send user input request
                await self._request_user_input(session_id, user_id)
                yield self._create_user_input_request_chunk(
                    self.get_user_input_prompt(session_id), session_id, context.user_id
                )
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan
        plan = await planning_task
        async for chunk in self._execute_plan_with_input_support(
            plan, user_input.meta.model_dump()
        ):
            yield chunk

    async def _request_user_input(self, session_id: str, _user_id: str):
        """Set session to require user input and send the request"""
        # Note: _user_id parameter kept for potential future use in user validation
        session = await self.session_manager.get_session(session_id)
        if session:
            session.require_user_input()
            await self.session_manager.update_session(session)

    def _validate_execution_context(
        self, context: ExecutionContext, user_id: str
    ) -> bool:
        """Validate execution context integrity"""
        if not hasattr(context, "stage") or not context.stage:
            return False

        if not context.validate_user(user_id):
            return False

        if context.is_expired():
            return False

        return True

    def _create_message_chunk(
        self,
        content: str,
        session_id: str,
        user_id: str,
        agent_name: str,
        kind: MessageDataKind = MessageDataKind.TEXT,
        is_final: bool = False,
        status: MessageChunkStatus = MessageChunkStatus.partial,
    ) -> MessageChunk:
        """Create a MessageChunk with standardized metadata"""
        return MessageChunk(
            content=content,
            kind=kind,
            meta=MessageChunkMetadata(
                session_id=session_id,
                user_id=user_id,
                agent_name=agent_name,
                status=status,
            ),
            is_final=is_final,
        )

    def _create_error_message_chunk(
        self, error_msg: str, session_id: str, user_id: str, agent_name: str
    ) -> MessageChunk:
        """Create an error MessageChunk with standardized format"""
        return self._create_message_chunk(
            content=f"(Error): {error_msg}",
            session_id=session_id,
            user_id=user_id,
            agent_name=agent_name,
            is_final=True,
            status=MessageChunkStatus.failure,
        )

    def _create_user_input_request_chunk(
        self,
        prompt: str,
        session_id: str,
        user_id: str,
        agent_name: str = "__planner__",
    ) -> MessageChunk:
        """Create a user input request MessageChunk"""
        return self._create_message_chunk(
            content=f"USER_INPUT_REQUIRED:{prompt}",
            session_id=session_id,
            user_id=user_id,
            agent_name=agent_name,
            kind=MessageDataKind.COMMAND,
            is_final=True,
            status=MessageChunkStatus.partial,
        )

    async def _continue_planning(
        self, session_id: str, context: ExecutionContext
    ) -> AsyncGenerator[MessageChunk, None]:
        """Resume planning stage execution"""
        planning_task = context.get_metadata("planning_task")
        original_user_input = context.get_metadata("original_user_input")

        if not all([planning_task, original_user_input]):
            yield self._create_error_message_chunk(
                "Invalid planning context - missing required data",
                session_id,
                context.user_id,
                "__planner__",
            )
            await self._cancel_execution(session_id)
            return

        # Continue monitoring planning task
        while not planning_task.done():
            if self.has_pending_user_input(session_id):
                # Still need more user input, send request
                prompt = self.get_user_input_prompt(session_id)
                # Ensure session is set to require user input again for repeated prompts
                await self._request_user_input(session_id, context.user_id)
                yield self._create_user_input_request_chunk(
                    prompt, session_id, context.user_id
                )
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan and clean up context
        plan = await planning_task
        del self._execution_contexts[session_id]

        async for chunk in self._execute_plan_with_input_support(
            plan, original_user_input.meta.model_dump()
        ):
            yield chunk

    async def _cancel_execution(self, session_id: str):
        """Cancel execution and clean up all related resources"""
        # Clean up execution context
        if session_id in self._execution_contexts:
            context = self._execution_contexts[session_id]

            # Cancel planning task if it exists and is not done
            planning_task = context.get_metadata("planning_task")
            if planning_task and not planning_task.done():
                planning_task.cancel()

            del self._execution_contexts[session_id]

        # Clear pending user input
        self.user_input_manager.clear_request(session_id)

        # Reset session status
        session = await self.session_manager.get_session(session_id)
        if session:
            session.activate()
            await self.session_manager.update_session(session)

    async def _cleanup_expired_contexts(
        self, max_age_seconds: int = DEFAULT_CONTEXT_TIMEOUT_SECONDS
    ):
        """Clean up execution contexts that have been idle for too long"""
        expired_sessions = [
            session_id
            for session_id, context in self._execution_contexts.items()
            if context.is_expired(max_age_seconds)
        ]

        for session_id in expired_sessions:
            await self._cancel_execution(session_id)
            logger.warning(
                f"Cleaned up expired execution context for session {session_id}"
            )

    # ==================== Plan and Task Execution Methods ====================

    async def _execute_plan_with_input_support(
        self, plan: ExecutionPlan, metadata: dict
    ) -> AsyncGenerator[MessageChunk, None]:
        """
        Execute an execution plan with Human-in-the-Loop support.

        This method streams execution results and handles user input interruptions
        during task execution.

        Args:
            plan: The execution plan containing tasks to execute
            metadata: Execution metadata containing session and user info
        """
        session_id, user_id = metadata["session_id"], metadata["user_id"]

        if not plan.tasks:
            yield self._create_error_message_chunk(
                "No tasks found for this request.", session_id, user_id, "__system__"
            )
            return

        # Track agent responses for session storage
        agent_responses = defaultdict(str)

        for task in plan.tasks:
            try:
                # Register the task with TaskManager
                await self.task_manager.store.save_task(task)

                # Execute task with input support
                async for chunk in self._execute_task_with_input_support(
                    task, plan.query, metadata
                ):
                    # Accumulate agent responses
                    agent_name = chunk.meta.agent_name
                    agent_responses[agent_name] += chunk.content
                    yield chunk

                    # Save complete responses to session
                    if chunk.is_final and agent_responses[agent_name].strip():
                        await self.session_manager.add_message(
                            session_id,
                            Role.AGENT,
                            agent_responses[agent_name],
                            agent_name=agent_name,
                        )
                        agent_responses[agent_name] = ""

            except Exception as e:
                error_msg = f"Error executing {task.agent_name}: {str(e)}"
                logger.exception(f"Task execution failed: {error_msg}")
                yield self._create_error_message_chunk(
                    error_msg, session_id, user_id, task.agent_name
                )

        # Save any remaining agent responses
        await self._save_remaining_responses(session_id, agent_responses)

    async def _execute_task_with_input_support(
        self, task: Task, query: str, metadata: dict
    ) -> AsyncGenerator[MessageChunk, None]:
        """
        Execute a single task with user input interruption support.

        Args:
            task: The task to execute
            query: The query/prompt for the task
            metadata: Execution metadata
        """
        try:
            # Start task execution
            await self.task_manager.start_task(task.task_id)

            # Get agent connection
            agent_card = await self.agent_connections.start_agent(
                task.agent_name,
                with_listener=False,
                notification_callback=store_task_in_session,
            )
            client = await self.agent_connections.get_client(task.agent_name)

            if not client:
                raise RuntimeError(f"Could not connect to agent {task.agent_name}")

            # Configure metadata for notifications
            if task.pattern != TaskPattern.ONCE:
                metadata["notify"] = True

            # Send message to agent
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

                if isinstance(event, TaskStatusUpdateEvent):
                    await self._handle_task_status_update(event, task)

                    # TODO: Check for user input requirement
                    # Handle task failure
                    if event.status.state == TaskState.failed:
                        err_msg = get_message_text(event.status.message)
                        await self.task_manager.fail_task(task.task_id, err_msg)
                        yield self._create_error_message_chunk(
                            err_msg, task.session_id, task.user_id, task.agent_name
                        )
                        return

                elif isinstance(event, TaskArtifactUpdateEvent):
                    yield self._create_message_chunk(
                        get_message_text(event.artifact, ""),
                        task.session_id,
                        task.user_id,
                        task.agent_name,
                        is_final=metadata.get("notify", False),
                    )

            # Complete task successfully
            await self.task_manager.complete_task(task.task_id)
            yield self._create_message_chunk(
                "",
                task.session_id,
                task.user_id,
                task.agent_name,
                is_final=True,
                status=MessageChunkStatus.success,
            )

        except Exception as e:
            await self.task_manager.fail_task(task.task_id, str(e))
            raise e

    async def _handle_task_status_update(
        self, event: TaskStatusUpdateEvent, task: Task
    ):
        """Handle task status update events"""
        logger.info(f"Task {task.task_id} status update: {event.status.state}")

        # Add any additional status-specific handling here
        if event.status.state == TaskState.submitted:
            # Task was submitted successfully
            pass
        elif event.status.state == TaskState.completed:
            # Task completed successfully
            pass

    async def _save_remaining_responses(self, session_id: str, agent_responses: dict):
        """Save any remaining agent responses to the session"""
        for agent_name, full_response in agent_responses.items():
            if full_response.strip():
                await self.session_manager.add_message(
                    session_id, Role.AGENT, full_response, agent_name=agent_name
                )

    # ==================== Legacy Task Execution (No HIL Support) ====================

    async def _execute_plan_legacy(
        self, plan: ExecutionPlan, metadata: dict
    ) -> AsyncGenerator[MessageChunk, None]:
        """
        Execute an execution plan without Human-in-the-Loop support.

        This is a simplified version for backwards compatibility.
        """
        session_id, user_id = metadata["session_id"], metadata["user_id"]

        if not plan.tasks:
            yield self._create_error_message_chunk(
                "No tasks found for this request.", session_id, user_id, "__system__"
            )
            return

        # Execute tasks sequentially
        for task in plan.tasks:
            try:
                await self.task_manager.store.save_task(task)
                async for chunk in self._execute_task_legacy(
                    task, plan.query, metadata
                ):
                    yield chunk
            except Exception as e:
                error_msg = f"Error executing {task.agent_name}: {str(e)}"
                yield self._create_error_message_chunk(
                    error_msg, session_id, user_id, task.agent_name
                )

    async def _execute_task_legacy(
        self, task: Task, query: str, metadata: dict
    ) -> AsyncGenerator[MessageChunk, None]:
        """
        Execute a single task without user input interruption support.

        This is a simplified version for backwards compatibility.
        """
        try:
            await self.task_manager.start_task(task.task_id)

            # Get agent connection
            agent_card = await self.agent_connections.start_agent(
                task.agent_name,
                with_listener=False,
                notification_callback=store_task_in_session,
            )
            client = await self.agent_connections.get_client(task.agent_name)

            if not client:
                raise RuntimeError(f"Could not connect to agent {task.agent_name}")

            if task.pattern != TaskPattern.ONCE:
                metadata["notify"] = True

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

                if isinstance(event, TaskStatusUpdateEvent):
                    logger.info(f"Task status update: {event.status.state}")

                    if event.status.state == TaskState.failed:
                        err_msg = get_message_text(event.status.message)
                        await self.task_manager.fail_task(task.task_id, err_msg)
                        yield self._create_error_message_chunk(
                            err_msg, task.session_id, task.user_id, task.agent_name
                        )
                        return
                    continue

                if isinstance(event, TaskArtifactUpdateEvent):
                    yield self._create_message_chunk(
                        get_message_text(event.artifact, ""),
                        task.session_id,
                        task.user_id,
                        task.agent_name,
                        is_final=metadata.get("notify", False),
                    )

            # Complete task
            await self.task_manager.complete_task(task.task_id)
            yield self._create_message_chunk(
                "",
                task.session_id,
                task.user_id,
                task.agent_name,
                is_final=True,
                status=MessageChunkStatus.success,
            )

        except Exception as e:
            await self.task_manager.fail_task(task.task_id, str(e))
            raise e


# ==================== Module-level Factory Function ====================

_orchestrator = AgentOrchestrator()


def get_default_orchestrator() -> AgentOrchestrator:
    """Get the default singleton instance of AgentOrchestrator"""
    return _orchestrator
