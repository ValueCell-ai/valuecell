import asyncio
import logging
from collections import defaultdict
from typing import AsyncGenerator, Dict, Optional

from a2a.types import TaskArtifactUpdateEvent, TaskState, TaskStatusUpdateEvent
from valuecell.core.agent.connect import get_default_remote_connections
from valuecell.core.agent.responses import EventPredicates
from valuecell.core.coordinate.response import ResponseFactory
from valuecell.core.coordinate.response_router import (
    RouteResult,
    SideEffectKind,
    handle_artifact_update,
    handle_status_update,
)
from valuecell.core.session import Role, SessionStatus, get_default_session_manager
from valuecell.core.task import Task, get_default_task_manager
from valuecell.core.task.models import TaskPattern
from valuecell.core.types import (
    BaseResponse,
    NotifyResponseEvent,
    StreamResponseEvent,
    UserInput,
)
from valuecell.utils.uuid import generate_thread_id

from .callback import store_task_in_session
from .models import ExecutionPlan
from .planner import ExecutionPlanner, UserInputRequest

logger = logging.getLogger(__name__)

# Constants for configuration
DEFAULT_CONTEXT_TIMEOUT_SECONDS = 3600  # 1 hour
ASYNC_SLEEP_INTERVAL = 0.1  # 100ms


class ExecutionContext:
    """Manages the state of an interrupted execution for resumption"""

    def __init__(self, stage: str, session_id: str, thread_id: str, user_id: str):
        self.stage = stage
        self.session_id = session_id
        self.thread_id = thread_id
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

        self._response_factory = ResponseFactory()

    # ==================== Public API Methods ====================

    async def process_user_input(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
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
            session = await self.session_manager.get_session(session_id)
            if not session:
                await self.session_manager.create_session(
                    user_id, session_id=session_id
                )
                session = await self.session_manager.get_session(session_id)
                yield self._response_factory.conversation_started(
                    conversation_id=session_id
                )

            # Handle session continuation vs new request
            if session.status == SessionStatus.REQUIRE_USER_INPUT:
                async for response in self._handle_session_continuation(user_input):
                    yield response
            else:
                async for response in self._handle_new_request(user_input):
                    yield response

        except Exception as e:
            logger.exception(f"Error processing user input for session {session_id}")
            yield self._response_factory.system_failed(
                session_id,
                f"(Error) Error processing request: {str(e)}",
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

    async def _handle_user_input_request(self, request: UserInputRequest):
        """Handle user input request from planner"""
        # Extract session_id from request context
        session_id = getattr(request, "session_id", None)
        if session_id:
            self.user_input_manager.add_request(session_id, request)

    async def _handle_session_continuation(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Handle continuation of an interrupted session"""
        session_id = user_input.meta.session_id
        user_id = user_input.meta.user_id

        # Validate execution context exists
        if session_id not in self._execution_contexts:
            yield self._response_factory.system_failed(
                session_id,
                "No execution context found for this session. The session may have expired.",
            )
            return

        context = self._execution_contexts[session_id]

        # Validate context integrity and user consistency
        if not self._validate_execution_context(context, user_id):
            yield self._response_factory.system_failed(
                session_id,
                "Invalid execution context or user mismatch.",
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
        # Resuming execution stage is not yet supported
        else:
            yield self._response_factory.system_failed(
                session_id,
                "Resuming execution stage is not yet supported.",
            )

    async def _handle_new_request(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Handle a new user request"""
        session_id = user_input.meta.session_id
        thread_id = generate_thread_id()

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
            planning_task, thread_id, user_input, context_aware_callback
        ):
            yield chunk

    def _create_context_aware_callback(self, session_id: str):
        """Create a callback that adds session context to user input requests"""

        async def context_aware_handle(request):
            request.session_id = session_id
            await self._handle_user_input_request(request)

        return context_aware_handle

    async def _monitor_planning_task(
        self,
        planning_task: asyncio.Task,
        thread_id: str,
        user_input: UserInput,
        callback,
    ) -> AsyncGenerator[BaseResponse, None]:
        """Monitor planning task and handle user input interruptions"""
        session_id = user_input.meta.session_id
        user_id = user_input.meta.user_id

        # Wait for planning completion or user input request
        while not planning_task.done():
            if self.has_pending_user_input(session_id):
                # Save planning context
                context = ExecutionContext("planning", session_id, thread_id, user_id)
                context.add_metadata(
                    original_user_input=user_input,
                    planning_task=planning_task,
                    planner_callback=callback,
                )
                self._execution_contexts[session_id] = context

                # Update session status and send user input request
                await self._request_user_input(session_id)
                yield self._response_factory.plan_require_user_input(
                    session_id, thread_id, self.get_user_input_prompt(session_id)
                )
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan
        plan = await planning_task
        async for chunk in self._execute_plan_with_input_support(plan, thread_id):
            yield chunk

    async def _request_user_input(self, session_id: str):
        """Set session to require user input and send the request"""
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

    async def _continue_planning(
        self, session_id: str, context: ExecutionContext
    ) -> AsyncGenerator[BaseResponse, None]:
        """Resume planning stage execution"""
        planning_task = context.get_metadata("planning_task")
        original_user_input = context.get_metadata("original_user_input")
        thread_id = generate_thread_id()
        context.thread_id = thread_id

        if not all([planning_task, original_user_input]):
            yield self._response_factory.plan_failed(
                session_id,
                thread_id,
                "Invalid planning context - missing required data",
            )
            await self._cancel_execution(session_id)
            return

        # Continue monitoring planning task
        while not planning_task.done():
            if self.has_pending_user_input(session_id):
                # Still need more user input, send request
                prompt = self.get_user_input_prompt(session_id)
                # Ensure session is set to require user input again for repeated prompts
                await self._request_user_input(session_id)
                yield self._response_factory.plan_require_user_input(
                    session_id, thread_id, prompt
                )
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan and clean up context
        plan = await planning_task
        del self._execution_contexts[session_id]

        async for message in self._execute_plan_with_input_support(plan, thread_id):
            yield message

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
        self, plan: ExecutionPlan, thread_id: str, metadata: Optional[dict] = None
    ) -> AsyncGenerator[BaseResponse, None]:
        """
        Execute an execution plan with Human-in-the-Loop support.

        This method streams execution results and handles user input interruptions
        during task execution.

        Args:
            plan: The execution plan containing tasks to execute
            metadata: Execution metadata containing session and user info
        """
        session_id = plan.session_id

        if not plan.tasks:
            yield self._response_factory.plan_failed(
                session_id, thread_id, "No tasks found for this request."
            )
            return

        # Track agent responses for session storage
        agent_responses = defaultdict(str)

        for task in plan.tasks:
            try:
                # Register the task with TaskManager
                await self.task_manager.store.save_task(task)

                # Execute task with input support
                async for response in self._execute_task_with_input_support(
                    task, thread_id, metadata
                ):
                    # Accumulate based on event
                    if response.event in {
                        StreamResponseEvent.MESSAGE_CHUNK,
                        StreamResponseEvent.REASONING,
                        NotifyResponseEvent.MESSAGE,
                    } and isinstance(response.data.payload.content, str):
                        agent_responses[task.agent_name] += (
                            response.data.payload.content
                        )
                    yield response

                    if (
                        EventPredicates.is_task_completed(response.event)
                        or task.pattern == TaskPattern.RECURRING
                    ):
                        if agent_responses[task.agent_name].strip():
                            await self.session_manager.add_message(
                                session_id,
                                Role.AGENT,
                                agent_responses[task.agent_name],
                                agent_name=task.agent_name,
                            )
                            agent_responses[task.agent_name] = ""

            except Exception as e:
                error_msg = f"(Error) Error executing {task.agent_name}: {str(e)}"
                logger.exception(f"Task execution failed: {error_msg}")
                yield self._response_factory.task_failed(
                    session_id,
                    thread_id,
                    task.task_id,
                    _generate_task_default_subtask_id(task.task_id),
                    error_msg,
                )

        # Save any remaining agent responses
        await self._save_remaining_responses(session_id, agent_responses)
        yield self._response_factory.done(session_id, thread_id)

    async def _execute_task_with_input_support(
        self, task: Task, thread_id: str, metadata: Optional[dict] = None
    ) -> AsyncGenerator[BaseResponse, None]:
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
            agent_name = task.agent_name
            agent_card = await self.agent_connections.start_agent(
                agent_name,
                with_listener=False,
                notification_callback=store_task_in_session,
            )
            client = await self.agent_connections.get_client(agent_name)
            if not client:
                raise RuntimeError(f"Could not connect to agent {agent_name}")

            # Configure metadata for notifications
            metadata = metadata or {}
            if task.pattern != TaskPattern.ONCE:
                metadata["notify"] = True

            # Send message to agent
            remote_response = await client.send_message(
                task.query,
                session_id=task.session_id,
                metadata=metadata,
                streaming=agent_card.capabilities.streaming,
            )

            # Process streaming responses
            async for remote_task, event in remote_response:
                if event is None and remote_task.status.state == TaskState.submitted:
                    task.remote_task_ids.append(remote_task.id)
                    continue

                if isinstance(event, TaskStatusUpdateEvent):
                    result: RouteResult = await handle_status_update(
                        self._response_factory, task, thread_id, event
                    )
                    for r in result.responses:
                        yield r
                    # Apply side effects
                    for eff in result.side_effects:
                        if eff.kind == SideEffectKind.FAIL_TASK:
                            await self.task_manager.fail_task(
                                task.task_id, eff.reason or ""
                            )
                    if result.done:
                        return
                    continue

                if isinstance(event, TaskArtifactUpdateEvent):
                    responses = await handle_artifact_update(
                        self._response_factory, task, thread_id, event
                    )
                    for r in responses:
                        yield r
                    continue

            # Complete task successfully
            await self.task_manager.complete_task(task.task_id)
            yield self._response_factory.task_completed(
                conversation_id=task.session_id,
                thread_id=thread_id,
                task_id=task.task_id,
                subtask_id=_generate_task_default_subtask_id(task.task_id),
            )

        except Exception as e:
            await self.task_manager.fail_task(task.task_id, str(e))
            raise e

    async def _save_remaining_responses(self, session_id: str, agent_responses: dict):
        """Save any remaining agent responses to the session"""
        for agent_name, full_response in agent_responses.items():
            if full_response.strip():
                await self.session_manager.add_message(
                    session_id, Role.AGENT, full_response, agent_name=agent_name
                )


def _generate_task_default_subtask_id(task_id: str) -> str:
    """Generate a default subtask ID based on the main task ID"""
    return f"{task_id}-default_subtask"


# ==================== Module-level Factory Function ====================

_orchestrator = AgentOrchestrator()


def get_default_orchestrator() -> AgentOrchestrator:
    """Get the default singleton instance of AgentOrchestrator"""
    return _orchestrator
