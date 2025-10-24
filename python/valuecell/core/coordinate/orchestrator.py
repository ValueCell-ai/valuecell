import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Optional

from a2a.types import TaskArtifactUpdateEvent, TaskState, TaskStatusUpdateEvent

from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.constants import (
    CURRENT_CONTEXT,
    DEPENDENCIES,
    LANGUAGE,
    METADATA,
    ORIGINAL_USER_INPUT,
    PLANNING_TASK,
    TIMEZONE,
    USER_PROFILE,
)
from valuecell.core.conversation import (
    ConversationManager,
    ConversationStatus,
    SQLiteConversationStore,
    SQLiteItemStore,
)
from valuecell.core.coordinate.models import ExecutionPlan
from valuecell.core.coordinate.planner import ExecutionPlanner, UserInputRequest
from valuecell.core.coordinate.response import ResponseFactory
from valuecell.core.coordinate.response_buffer import ResponseBuffer, SaveItem
from valuecell.core.coordinate.response_router import (
    RouteResult,
    SideEffectKind,
    handle_status_update,
)
from valuecell.core.coordinate.super_agent import (
    SuperAgent,
    SuperAgentDecision,
    SuperAgentOutcome,
)
from valuecell.core.task import Task, TaskManager
from valuecell.core.task.models import TaskPattern
from valuecell.core.types import (
    BaseResponse,
    ComponentType,
    ConversationItemEvent,
    StreamResponseEvent,
    SubagentConversationPhase,
    UserInput,
)
from valuecell.utils import resolve_db_path
from valuecell.utils.i18n_utils import get_current_language, get_current_timezone
from valuecell.utils.uuid import generate_item_id, generate_task_id, generate_thread_id

logger = logging.getLogger(__name__)

# Constants for configuration
DEFAULT_CONTEXT_TIMEOUT_SECONDS = 3600  # 1 hour
ASYNC_SLEEP_INTERVAL = 0.1  # 100ms


class ExecutionContext:
    """Manage the state of an interrupted execution for later resumption.

    ExecutionContext stores lightweight metadata about an in-flight plan or
    task execution that has been paused waiting for user input. The context
    records the stage (e.g. "planning"), the conversation/thread identifiers,
    the original requesting user, and a timestamp used for expiration.
    """

    def __init__(self, stage: str, conversation_id: str, thread_id: str, user_id: str):
        self.stage = stage
        self.conversation_id = conversation_id
        self.thread_id = thread_id
        self.user_id = user_id
        self.created_at = asyncio.get_event_loop().time()
        self.metadata: Dict = {}

    def is_expired(
        self, max_age_seconds: int = DEFAULT_CONTEXT_TIMEOUT_SECONDS
    ) -> bool:
        """Return True when the context is older than the configured TTL."""
        current_time = asyncio.get_event_loop().time()
        return current_time - self.created_at > max_age_seconds

    def validate_user(self, user_id: str) -> bool:
        """Validate that the user ID matches the original request"""
        return self.user_id == user_id

    def add_metadata(self, **kwargs):
        """Attach arbitrary key/value metadata to this execution context."""
        self.metadata.update(kwargs)

    def get_metadata(self, key: str, default=None):
        """Get metadata value"""
        return self.metadata.get(key, default)


class UserInputManager:
    """Manage pending Human-in-the-Loop user input requests.

    This simple manager stores `UserInputRequest` objects keyed by
    `conversation_id`. Callers can add requests, query for prompts and provide
    responses which will wake any awaiting tasks.
    """

    def __init__(self):
        self._pending_requests: Dict[str, UserInputRequest] = {}

    def add_request(self, conversation_id: str, request: UserInputRequest):
        """Register a pending user input request for a conversation."""
        self._pending_requests[conversation_id] = request

    def has_pending_request(self, conversation_id: str) -> bool:
        """Check if there's a pending request for the conversation"""
        return conversation_id in self._pending_requests

    def get_request_prompt(self, conversation_id: str) -> Optional[str]:
        """Return the prompt text for a pending request, or None if none found."""
        request = self._pending_requests.get(conversation_id)
        return request.prompt if request else None

    def provide_response(self, conversation_id: str, response: str) -> bool:
        """Supply the user's response to a pending request and complete it.

        Returns True when the response was accepted and the pending request
        removed; False when no pending request existed for the conversation.
        """
        if conversation_id not in self._pending_requests:
            return False

        request = self._pending_requests[conversation_id]
        request.provide_response(response)
        del self._pending_requests[conversation_id]
        return True

    def clear_request(self, conversation_id: str):
        """Clear a pending request"""
        self._pending_requests.pop(conversation_id, None)


class AgentOrchestrator:
    """
    Orchestrates execution of user requests through multiple agents with Human-in-the-Loop support.

    This class manages the entire lifecycle of user requests including:
    - Planning phase with user input collection
    - Task execution with interruption support
    - Conversation state management
    - Error handling and recovery
    """

    def __init__(self):
        db_path = resolve_db_path()
        self.conversation_manager = ConversationManager(
            conversation_store=SQLiteConversationStore(db_path=db_path),
            item_store=SQLiteItemStore(db_path=db_path),
        )
        self.task_manager = TaskManager()
        self.agent_connections = RemoteConnections()

        # Initialize user input management
        self.user_input_manager = UserInputManager()

        # Initialize execution context management
        self._execution_contexts: Dict[str, ExecutionContext] = {}

        # Initialize planner
        self.planner = ExecutionPlanner(self.agent_connections)

        # Initialize Super Agent (triage/frontline agent)
        self.super_agent = SuperAgent()

        self._response_factory = ResponseFactory()
        # Buffer for streaming responses -> persisted ConversationItems
        self._response_buffer = ResponseBuffer()

    # ==================== Public API Methods ====================

    async def process_user_input(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """
        Main entry point for processing user input with optional
        Human-in-the-Loop interactions.

        The orchestrator yields streaming `BaseResponse` objects that callers
        (for example, an HTTP SSE endpoint or WebSocket) can forward to the
        client. This method handles:
        - Starting new plans when no execution context exists
        - Resuming paused executions when conversation state requires input
        - Directly providing responses to existing pending prompts

        Args:
            user_input: The user's input, including conversation metadata.

        Yields:
            BaseResponse instances representing streaming chunks, status,
            or terminal messages for the request.
        """
        conversation_id = user_input.meta.conversation_id
        user_id = user_input.meta.user_id

        try:
            # Ensure conversation exists
            conversation = await self.conversation_manager.get_conversation(
                conversation_id
            )
            if not conversation:
                await self.conversation_manager.create_conversation(
                    user_id, conversation_id=conversation_id
                )
                conversation = await self.conversation_manager.get_conversation(
                    conversation_id
                )
                yield self._response_factory.conversation_started(
                    conversation_id=conversation_id
                )

            # Handle conversation continuation vs new request
            if conversation.status == ConversationStatus.REQUIRE_USER_INPUT:
                async for response in self._handle_conversation_continuation(
                    user_input
                ):
                    yield response
            else:
                async for response in self._handle_new_request(user_input):
                    yield response

        except Exception as e:
            logger.exception(
                f"Error processing user input for conversation {conversation_id}"
            )
            yield self._response_factory.system_failed(
                conversation_id,
                f"(Error) Error processing request: {str(e)}",
            )
        finally:
            yield self._response_factory.done(conversation_id)

    async def provide_user_input(self, conversation_id: str, response: str):
        """Submit a user's response to a pending input request.

        When a planner has requested clarification (Human-in-the-Loop), the
        orchestrator stores a `UserInputRequest`. Calling this method provides
        the response, updates the conversation state to active, and wakes any
        awaiting planner logic.

        Args:
            conversation_id: Conversation where a pending input request exists.
            response: The textual response supplied by the user.
        """
        if self.user_input_manager.provide_response(conversation_id, response):
            # Update conversation status to active
            conversation = await self.conversation_manager.get_conversation(
                conversation_id
            )
            if conversation:
                conversation.activate()
                await self.conversation_manager.update_conversation(conversation)

    def has_pending_user_input(self, conversation_id: str) -> bool:
        """Return True if the conversation currently awaits user input."""
        return self.user_input_manager.has_pending_request(conversation_id)

    def get_user_input_prompt(self, conversation_id: str) -> Optional[str]:
        """Return the prompt text for a pending user-input request, or None.

        This is useful for displaying the outstanding prompt to the user or
        embedding it into UI flows.
        """
        return self.user_input_manager.get_request_prompt(conversation_id)

    async def close_conversation(self, conversation_id: str):
        """Close a conversation and clean up resources.

        This cancels any running tasks for the conversation, clears execution
        contexts and pending user-input requests, and resets conversation
        status to active when appropriate.
        """
        # Cancel any running tasks for this conversation
        await self.task_manager.cancel_conversation_tasks(conversation_id)

        # Clean up execution context
        await self._cancel_execution(conversation_id)

    async def get_conversation_history(
        self,
        conversation_id: Optional[str] = None,
        event: Optional[ConversationItemEvent] = None,
        component_type: Optional[str] = None,
    ) -> list[BaseResponse]:
        """Return the persisted conversation history as a list of responses.

        Args:
            conversation_id: The conversation to retrieve history for.
            event: Optional filter to include only items with this event type.
            component_type: Optional filter to include only items with this component type.

        Returns:
            A list of `BaseResponse` instances reconstructed from persisted
            ConversationItems.
        """
        items = await self.conversation_manager.get_conversation_items(
            conversation_id=conversation_id, event=event, component_type=component_type
        )
        return [self._response_factory.from_conversation_item(it) for it in items]

    async def cleanup(self):
        """Perform graceful cleanup of orchestrator-managed resources.

        This will remove expired execution contexts and stop all remote agent
        connections/listeners managed by the orchestrator.
        """
        await self._cleanup_expired_contexts()
        await self.agent_connections.stop_all()

    # ==================== Private Helper Methods ====================

    async def _handle_user_input_request(self, request: UserInputRequest):
        """Register an incoming `UserInputRequest` produced by the planner.

        The planner may emit UserInputRequest objects when it requires
        clarification. This helper extracts the `conversation_id` from the
        request and registers it with the `UserInputManager` so callers can
        later provide the response.
        """
        # Extract conversation_id from request context
        conversation_id = getattr(request, "conversation_id", None)
        if conversation_id:
            self.user_input_manager.add_request(conversation_id, request)

    async def _handle_conversation_continuation(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Resume an interrupted execution after the user provided requested input.

        This method validates the existing `ExecutionContext`, records the new
        thread id for this resumed interaction, and either continues planning
        or indicates that resuming execution is not supported for other stages.

        It yields the generated streaming responses (thread start and subsequent
        planner/execution messages) back to the caller.
        """
        conversation_id = user_input.meta.conversation_id
        user_id = user_input.meta.user_id

        # Validate execution context exists
        if conversation_id not in self._execution_contexts:
            yield self._response_factory.system_failed(
                conversation_id,
                "No execution context found for this conversation. The conversation may have expired.",
            )
            return

        context = self._execution_contexts[conversation_id]

        # Validate context integrity and user consistency
        if not self._validate_execution_context(context, user_id):
            yield self._response_factory.system_failed(
                conversation_id,
                "Invalid execution context or user mismatch.",
            )
            await self._cancel_execution(conversation_id)
            return

        thread_id = generate_thread_id()
        response = self._response_factory.thread_started(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_query=user_input.query,
            agent_name=user_input.target_agent_name,
        )
        await self._persist_from_buffer(response)
        yield response

        # Provide user response and resume execution
        # If we are in an execution stage, store the pending response for resume
        context.add_metadata(pending_response=user_input.query)
        await self.provide_user_input(conversation_id, user_input.query)
        context.thread_id = thread_id

        # Resume based on execution stage
        if context.stage == "planning":
            async for response in self._continue_planning(
                conversation_id, thread_id, context
            ):
                yield response
        # Resuming execution stage is not yet supported
        else:
            yield self._response_factory.system_failed(
                conversation_id,
                "Resuming execution stage is not yet supported.",
            )

    async def _handle_new_request(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Start planning and execution for a new user request.

        This creates a planner task (executed asynchronously) and yields
        streaming responses produced during planning and subsequent execution.
        """
        conversation_id = user_input.meta.conversation_id
        thread_id = generate_thread_id()
        response = self._response_factory.thread_started(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_query=user_input.query,
            agent_name=user_input.target_agent_name,
        )
        await self._persist_from_buffer(response)
        yield response

        # 1) Super Agent triage phase (pre-planning) - skip if target agent is specified
        if user_input.target_agent_name == self.super_agent.name:
            super_outcome: SuperAgentOutcome = await self.super_agent.run(user_input)
            if super_outcome.decision == SuperAgentDecision.ANSWER:
                ans = self._response_factory.message_response_general(
                    StreamResponseEvent.MESSAGE_CHUNK,
                    conversation_id,
                    thread_id,
                    task_id=generate_task_id(),
                    content=super_outcome.answer_content,
                    agent_name=self.super_agent.name,
                )
                await self._persist_from_buffer(ans)
                yield ans
                return

            if super_outcome.decision == SuperAgentDecision.HANDOFF_TO_PLANNER:
                user_input.target_agent_name = ""
                user_input.query = super_outcome.enriched_query

        # 2) Planner phase (existing logic)
        # Create planning task with user input callback
        context_aware_callback = self._create_context_aware_callback(conversation_id)
        planning_task = asyncio.create_task(
            self.planner.create_plan(user_input, context_aware_callback, thread_id)
        )

        # Monitor planning progress
        async for response in self._monitor_planning_task(
            planning_task, thread_id, user_input, context_aware_callback
        ):
            yield response

    def _create_context_aware_callback(self, conversation_id: str):
        """Return an async callback that tags UserInputRequest objects with the
        conversation_id and forwards them to the orchestrator's handler.

        The planner receives this callback and can call it whenever it needs
        to request additional information from the end-user; the callback
        ensures the request is associated with the correct conversation.
        """

        async def context_aware_handle(request):
            request.conversation_id = conversation_id
            await self._handle_user_input_request(request)

        return context_aware_handle

    async def _monitor_planning_task(
        self,
        planning_task: asyncio.Task,
        thread_id: str,
        user_input: UserInput,
        callback,
    ) -> AsyncGenerator[BaseResponse, None]:
        """Monitor an in-progress planning task and handle interruptions.

        While the planner is running this loop watches for pending user input
        requests. If the planner pauses for clarification, the method records
        the planning context and yields a `plan_require_user_input` response
        to the caller. When planning completes, the produced `ExecutionPlan`
        is executed.
        """
        conversation_id = user_input.meta.conversation_id
        user_id = user_input.meta.user_id

        # Wait for planning completion or user input request
        while not planning_task.done():
            if self.has_pending_user_input(conversation_id):
                # Save planning context
                context = ExecutionContext(
                    "planning", conversation_id, thread_id, user_id
                )
                context.add_metadata(
                    original_user_input=user_input,
                    planning_task=planning_task,
                    planner_callback=callback,
                )
                self._execution_contexts[conversation_id] = context

                # Update conversation status and send user input request
                await self._request_user_input(conversation_id)
                response = self._response_factory.plan_require_user_input(
                    conversation_id,
                    thread_id,
                    self.get_user_input_prompt(conversation_id),
                )
                await self._persist_from_buffer(response)
                yield response
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan
        plan = await planning_task
        async for response in self._execute_plan_with_input_support(
            plan, conversation_id, thread_id
        ):
            yield response

    async def _request_user_input(self, conversation_id: str):
        """Set conversation to require user input and send the request"""
        conversation = await self.conversation_manager.get_conversation(conversation_id)
        if conversation:
            conversation.require_user_input()
            await self.conversation_manager.update_conversation(conversation)

    def _validate_execution_context(
        self, context: ExecutionContext, user_id: str
    ) -> bool:
        """Return True if the execution context appears intact and valid.

        Checks include presence of a stage, matching user id and TTL-based
        expiration.
        """
        if not hasattr(context, "stage") or not context.stage:
            return False

        if not context.validate_user(user_id):
            return False

        if context.is_expired():
            return False

        return True

    async def _continue_planning(
        self, conversation_id: str, thread_id: str, context: ExecutionContext
    ) -> AsyncGenerator[BaseResponse, None]:
        """Resume a previously-paused planning task and continue execution.

        If required pieces of the planning context are missing this method
        fails the plan and cancels the execution. Otherwise it waits for the
        planner to finish, handling repeated user-input prompts if needed,
        and then proceeds to execute the resulting plan.
        """
        planning_task = context.get_metadata(PLANNING_TASK)
        original_user_input = context.get_metadata(ORIGINAL_USER_INPUT)

        if not all([planning_task, original_user_input]):
            yield self._response_factory.plan_failed(
                conversation_id,
                thread_id,
                "Invalid planning context - missing required data",
            )
            await self._cancel_execution(conversation_id)
            return

        # Continue monitoring planning task
        while not planning_task.done():
            if self.has_pending_user_input(conversation_id):
                # Still need more user input, send request
                prompt = self.get_user_input_prompt(conversation_id)
                # Ensure conversation is set to require user input again for repeated prompts
                await self._request_user_input(conversation_id)
                response = self._response_factory.plan_require_user_input(
                    conversation_id, thread_id, prompt
                )
                await self._persist_from_buffer(response)
                yield response
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan and clean up context
        plan = await planning_task
        del self._execution_contexts[conversation_id]

        async for response in self._execute_plan_with_input_support(
            plan, conversation_id, thread_id
        ):
            yield response

    async def _cancel_execution(self, conversation_id: str):
        """Cancel and clean up any execution resources associated with a
        conversation.

        This cancels the planner task (if present), removes the execution
        context and clears any pending user input. It also resets the
        conversation's status back to active.
        """
        # Clean up execution context
        if conversation_id in self._execution_contexts:
            context = self._execution_contexts[conversation_id]

            # Cancel planning task if it exists and is not done
            planning_task = context.get_metadata(PLANNING_TASK)
            if planning_task and not planning_task.done():
                planning_task.cancel()

            del self._execution_contexts[conversation_id]

        # Clear pending user input
        self.user_input_manager.clear_request(conversation_id)

        # Reset conversation status
        conversation = await self.conversation_manager.get_conversation(conversation_id)
        if conversation:
            conversation.activate()
            await self.conversation_manager.update_conversation(conversation)

    async def _cleanup_expired_contexts(
        self, max_age_seconds: int = DEFAULT_CONTEXT_TIMEOUT_SECONDS
    ):
        """Sweep and remove execution contexts older than `max_age_seconds`.

        For each expired context the method cancels execution and logs a
        warning so the operator can investigate frequent expirations.
        """
        expired_conversations = [
            conversation_id
            for conversation_id, context in self._execution_contexts.items()
            if context.is_expired(max_age_seconds)
        ]

        for conversation_id in expired_conversations:
            await self._cancel_execution(conversation_id)
            logger.warning(
                f"Cleaned up expired execution context for conversation {conversation_id}"
            )

    # ==================== Plan and Task Execution Methods ====================

    async def _execute_plan_with_input_support(
        self,
        plan: ExecutionPlan,
        conversation_id: str,
        thread_id: str,
        metadata: Optional[dict] = None,
    ) -> AsyncGenerator[BaseResponse, None]:
        """
        Execute an execution plan with Human-in-the-Loop support.

        This method streams execution results and handles user input interruptions
        during task execution.

        Args:
            plan: The execution plan containing tasks to execute.
            metadata: Optional execution metadata containing conversation and user info.

        Yields:
            Streaming `BaseResponse` objects produced by each task execution.
        """

        for task in plan.tasks:
            subagent_conversation_item_id = generate_item_id()
            subagent_component_content_dict = {
                "conversation_id": task.conversation_id,
                "agent_name": task.agent_name,
                "phase": SubagentConversationPhase.START.value,
            }
            await self.conversation_manager.create_conversation(
                plan.user_id, conversation_id=task.conversation_id
            )
            if task.handoff_from_super_agent:
                yield self._response_factory.component_generator(
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    task_id=task.task_id,
                    content=json.dumps(subagent_component_content_dict),
                    component_type=ComponentType.SUBAGENT_CONVERSATION.value,
                    component_id=subagent_conversation_item_id,
                    agent_name=task.agent_name,
                )
                yield self._response_factory.thread_started(
                    conversation_id=task.conversation_id,
                    thread_id=thread_id,
                    user_query=task.query,
                )
            try:
                # Register the task with TaskManager (persist in-memory)
                await self.task_manager.update_task(task)

                # Execute task with input support
                async for response in self._execute_task_with_input_support(
                    task, thread_id, metadata
                ):
                    # Ensure buffered events carry a stable paragraph item_id
                    annotated = self._response_buffer.annotate(response)
                    # Accumulate based on event
                    yield annotated

                    # Persist via ResponseBuffer
                    await self._persist_from_buffer(annotated)

            except Exception as e:
                error_msg = f"(Error) Error executing {task.task_id}: {str(e)}"
                logger.exception(f"Task execution failed: {error_msg}")
                yield self._response_factory.task_failed(
                    conversation_id,
                    thread_id,
                    task.task_id,
                    error_msg,
                    agent_name=task.agent_name,
                )
            finally:
                if task.handoff_from_super_agent:
                    subagent_component_content_dict["phase"] = (
                        SubagentConversationPhase.END.value
                    )
                    yield self._response_factory.component_generator(
                        conversation_id=conversation_id,
                        thread_id=thread_id,
                        task_id=task.task_id,
                        content=json.dumps(subagent_component_content_dict),
                        component_type=ComponentType.SUBAGENT_CONVERSATION.value,
                        component_id=subagent_conversation_item_id,
                        agent_name=task.agent_name,
                    )

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
            task_id = task.task_id
            conversation_id = task.conversation_id

            await self.task_manager.start_task(task_id)
            # Get agent connection
            agent_name = task.agent_name
            agent_card = await self.agent_connections.start_agent(
                agent_name,
                with_listener=False,
            )
            client = await self.agent_connections.get_client(agent_name)
            if not client:
                raise RuntimeError(f"Could not connect to agent {agent_name}")

            # Configure A2A metadata
            metadata = metadata or {}
            if task.pattern != TaskPattern.ONCE:
                metadata["notify"] = True

            # Configure Agno metadata, reference: https://docs.agno.com/examples/concepts/agent/other/agent_run_metadata#agent-run-metadata
            metadata[METADATA] = {}

            # Configure Agno dependencies, reference: https://docs.agno.com/concepts/teams/dependencies#dependencies
            metadata[DEPENDENCIES] = {
                USER_PROFILE: {},
                CURRENT_CONTEXT: {},
                LANGUAGE: get_current_language(),
                TIMEZONE: get_current_timezone(),
            }

            # Send message to agent
            remote_response = await client.send_message(
                task.query,
                conversation_id=conversation_id,
                metadata=metadata,
                streaming=agent_card.capabilities.streaming,
            )

            # Process streaming responses
            async for remote_task, event in remote_response:
                if event is None and remote_task.status.state == TaskState.submitted:
                    task.remote_task_ids.append(remote_task.id)
                    yield self._response_factory.task_started(
                        conversation_id=conversation_id,
                        thread_id=thread_id,
                        task_id=task_id,
                        agent_name=task.agent_name,
                    )
                    continue

                if isinstance(event, TaskStatusUpdateEvent):
                    result: RouteResult = await handle_status_update(
                        self._response_factory, task, thread_id, event
                    )
                    for r in result.responses:
                        r = self._response_buffer.annotate(r)
                        yield r
                    # Apply side effects
                    for eff in result.side_effects:
                        if eff.kind == SideEffectKind.FAIL_TASK:
                            await self.task_manager.fail_task(task_id, eff.reason or "")
                    if result.done:
                        return
                    continue

                if isinstance(event, TaskArtifactUpdateEvent):
                    logger.info(
                        f"Received unexpected artifact update for task {task_id}: {event}"
                    )
                    continue

            # Complete task successfully
            await self.task_manager.complete_task(task_id)
            yield self._response_factory.task_completed(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                agent_name=task.agent_name,
            )
            # Finalize buffered aggregates for this task (explicit flush at task end)
            items = self._response_buffer.flush_task(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
            )
            await self._persist_items(items)

        except Exception as e:
            # On failure, finalize any buffered aggregates for this task
            items = self._response_buffer.flush_task(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
            )
            await self._persist_items(items)
            await self.task_manager.fail_task(task_id, str(e))
            raise e

    async def _persist_from_buffer(self, response: BaseResponse):
        """Ingest a response into the buffer and persist any SaveMessages produced."""
        items = self._response_buffer.ingest(response)
        await self._persist_items(items)

    async def _persist_items(self, items: list[SaveItem]):
        """Persist a list of SaveItems to the conversation manager."""
        for it in items:
            await self.conversation_manager.add_item(
                role=it.role,
                event=it.event,
                conversation_id=it.conversation_id,
                thread_id=it.thread_id,
                task_id=it.task_id,
                payload=it.payload,
                item_id=it.item_id,
                agent_name=it.agent_name,
            )
