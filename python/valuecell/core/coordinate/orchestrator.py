import asyncio
from typing import AsyncGenerator, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger

from valuecell.core.constants import ORIGINAL_USER_INPUT, PLANNING_TASK
from valuecell.core.conversation import ConversationService, ConversationStatus
from valuecell.core.event import EventResponseService
from valuecell.core.plan import PlanService
from valuecell.core.plan.models import ExecutionPlan
from valuecell.core.super_agent import SuperAgentService
from valuecell.core.task import TaskExecutor
from valuecell.core.types import (
    BaseResponse,
    StreamResponseEvent,
    UserInput,
)
from valuecell.utils import i18n_utils
from valuecell.utils.uuid import generate_task_id, generate_thread_id, generate_uuid

from .services import AgentServiceBundle

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


class AgentOrchestrator:
    """Coordinate planning, execution, and persistence across services."""

    def __init__(
        self,
        conversation_service: ConversationService | None = None,
        event_service: EventResponseService | None = None,
        plan_service: PlanService | None = None,
        super_agent_service: SuperAgentService | None = None,
        task_executor: TaskExecutor | None = None,
    ) -> None:
        services = AgentServiceBundle.compose(
            conversation_service=conversation_service,
            event_service=event_service,
            plan_service=plan_service,
            super_agent_service=super_agent_service,
            task_executor=task_executor,
        )

        self.conversation_service = services.conversation_service
        self.event_service = services.event_service
        self.super_agent_service = services.super_agent_service
        self.plan_service = services.plan_service
        self.task_executor = services.task_executor

        # Execution contexts keep track of paused planner runs.
        self._execution_contexts: Dict[str, ExecutionContext] = {}

    # ==================== Public API Methods ====================

    async def stream_react_agent(
        self, user_input: UserInput, _response_thread_id: str
    ) -> AsyncGenerator[BaseResponse, None]:
        """
        Stream React Agent (LangGraph) execution as standardized protocol events.

        This function orchestrates the React Agent's multi-node graph execution
        and converts internal LangGraph events into the frontend event protocol.

        Event Mappings:
        - Planner output -> MESSAGE_CHUNK (TODO: Consider REASONING)
        - Executor tasks -> TOOL_CALL_STARTED/COMPLETED (paired with consistent IDs)
        - Critic feedback -> MESSAGE_CHUNK (TODO: Consider REASONING)
        - Summarizer/Inquirer text -> MESSAGE_CHUNK

        Args:
            user_input: User input containing query and conversation context

        Yields:
            BaseResponse: Standardized protocol events for frontend consumption
        """
        from valuecell.agents.react_agent.graph import get_app

        conversation_id = user_input.meta.conversation_id

        # ID Mapping:
        # - LangGraph thread_id = conversation_id (for persistence)
        # - EventService thread_id = freshly generated (transient stream session)
        graph_thread_id = conversation_id
        root_task_id = generate_task_id()

        logger.info(
            "stream_react_agent: starting React Agent stream for conversation {}",
            conversation_id,
        )

        graph = get_app()
        user_context = {
            "language": i18n_utils.get_current_language(),
            "timezone": i18n_utils.get_current_timezone(),
        }
        # TODO: append previous conversation history after restart
        inputs = {
            "messages": [HumanMessage(content=user_input.query)],
            "user_context": user_context,
        }
        config = {"configurable": {"thread_id": graph_thread_id}}

        # Note: executor task pairing will read tool info from executor output.
        # No STARTED->COMPLETED mapping stored here (executor provides `tool`/`tool_name`).

        def is_real_node_output(d: dict) -> bool:
            """Filter out router string outputs (e.g., 'wait', 'plan')."""
            output = d.get("output")
            return not isinstance(output, str)

        try:
            async for event in graph.astream_events(
                inputs, config=config, version="v2"
            ):
                kind = event.get("event", "")
                node = event.get("metadata", {}).get("langgraph_node", "")
                data = event.get("data") or {}

                # =================================================================
                # 1. PLANNER -> MESSAGE_CHUNK (TODO: Consider REASONING)
                # =================================================================
                if kind == "on_chain_end" and node == "planner":
                    if is_real_node_output(data):
                        output = data.get("output", {})
                        if isinstance(output, dict) and "plan" in output:
                            plan = output.get("plan", [])
                            reasoning = output.get("strategy_update") or "..."

                            # Format plan as markdown
                            plan_md = f"\n\n**📅 Plan Updated:**\n*{reasoning}*\n"
                            for task in plan:
                                desc = task.get("description", "No description")
                                plan_md += f"- {desc}\n"

                            # TODO: Consider switching to event_service.reasoning()
                            yield await self.event_service.emit(
                                self.event_service.factory.message_response_general(
                                    event=StreamResponseEvent.MESSAGE_CHUNK,
                                    conversation_id=conversation_id,
                                    thread_id=_response_thread_id,
                                    task_id=root_task_id,
                                    content=plan_md,
                                    agent_name="Planner",
                                )
                            )

                # =================================================================
                # 2. EXECUTOR -> TOOL_CALL (STARTED & COMPLETED)
                # =================================================================

                # ---------------------------------------------------------
                # Case A: Executor STARTED
                # ---------------------------------------------------------
                elif kind == "on_chain_start" and node == "executor":
                    task_data = data.get("input", {}).get("task", {})
                    task_id = task_data.get("id")
                    raw_tool_name = task_data.get("tool_name", "unknown_tool")
                    task_description = task_data.get("description", "")

                    # [Optimization] Combine description and tool name for UI
                    # Format: "Get Stock Price (web_search)"
                    if task_description:
                        # Optional: Truncate description if it's too long for a header
                        short_desc = (
                            (task_description[:60] + "...")
                            if len(task_description) > 60
                            else task_description
                        )
                        display_tool_name = f"{short_desc} ({raw_tool_name})"
                    else:
                        display_tool_name = raw_tool_name

                    if task_id:
                        yield await self.event_service.emit(
                            self.event_service.factory.tool_call(
                                conversation_id=conversation_id,
                                thread_id=_response_thread_id,
                                task_id=root_task_id,
                                event=StreamResponseEvent.TOOL_CALL_STARTED,
                                tool_call_id=task_id,
                                tool_name=display_tool_name,
                                agent_name="Executor",
                            )
                        )

                # ---------------------------------------------------------
                # Case B: Executor COMPLETED
                # ---------------------------------------------------------
                elif kind == "on_chain_end" and node == "executor":
                    if is_real_node_output(data):
                        output = data.get("output", {})
                        if isinstance(output, dict) and "completed_tasks" in output:
                            for task_id_key, res in output["completed_tasks"].items():
                                # 1. Extract Result
                                if isinstance(res, dict):
                                    # Try to get 'result' field, fallback to full dict dump
                                    raw_result = res.get("result") or str(res)

                                    # Try to retrieve metadata preserved by executor
                                    res_tool_name = (
                                        res.get("tool_name") or "completed_tool"
                                    )
                                    res_description = res.get("description")
                                else:
                                    raw_result = str(res)
                                    res_tool_name = "completed_tool"
                                    res_description = None

                                # 2. Re-construct the display name to match STARTED event
                                # This ensures the UI updates the correct item instead of creating a new one
                                if res_description:
                                    short_desc = (
                                        (res_description[:60] + "...")
                                        if len(res_description) > 60
                                        else res_description
                                    )
                                    display_tool_name = (
                                        f"{short_desc} ({res_tool_name})"
                                    )
                                else:
                                    display_tool_name = res_tool_name

                                yield await self.event_service.emit(
                                    self.event_service.factory.tool_call(
                                        conversation_id=conversation_id,
                                        thread_id=_response_thread_id,
                                        task_id=root_task_id,
                                        event=StreamResponseEvent.TOOL_CALL_COMPLETED,
                                        tool_call_id=task_id_key,
                                        tool_name=display_tool_name,
                                        tool_result=raw_result,
                                        agent_name="Executor",
                                    )
                                )

                # =================================================================
                # 3. CRITIC -> MESSAGE_CHUNK (TODO: Consider REASONING)
                # =================================================================
                elif kind == "on_chain_end" and node == "critic":
                    if is_real_node_output(data):
                        output = data.get("output", {})
                        if isinstance(output, dict):
                            summary = output.get("_critic_summary")
                            if summary:
                                approved = summary.get("approved", False)
                                icon = "✅" if approved else "🚧"
                                reason = summary.get("reason") or summary.get(
                                    "feedback", ""
                                )

                                critic_md = (
                                    f"\n\n**{icon} Critic Decision:** {reason}\n\n"
                                )

                                # TODO: Consider switching to event_service.reasoning()
                                yield await self.event_service.emit(
                                    self.event_service.factory.message_response_general(
                                        event=StreamResponseEvent.MESSAGE_CHUNK,
                                        conversation_id=conversation_id,
                                        thread_id=_response_thread_id,
                                        task_id=root_task_id,
                                        content=critic_md,
                                        agent_name="Critic",
                                    )
                                )

                # =================================================================
                # 4. SUMMARIZER / INQUIRER -> MESSAGE_CHUNK
                # =================================================================

                # Summarizer: Streaming content
                elif kind == "on_chat_model_stream" and node == "summarizer":
                    chunk = data.get("chunk")
                    text = chunk.content if chunk else None
                    if text:
                        yield await self.event_service.emit(
                            self.event_service.factory.message_response_general(
                                event=StreamResponseEvent.MESSAGE_CHUNK,
                                conversation_id=conversation_id,
                                thread_id=_response_thread_id,
                                task_id=root_task_id,
                                content=text,
                                agent_name="Summarizer",
                            )
                        )

                # Inquirer: Static content (full message at end)
                elif kind == "on_chain_end" and node == "inquirer":
                    if is_real_node_output(data):
                        output = data.get("output", {})
                        msgs = output.get("messages", [])
                        if msgs and isinstance(msgs, list):
                            last_msg = msgs[-1]
                            if isinstance(last_msg, AIMessage) and last_msg.content:
                                yield await self.event_service.emit(
                                    self.event_service.factory.message_response_general(
                                        event=StreamResponseEvent.MESSAGE_CHUNK,
                                        conversation_id=conversation_id,
                                        thread_id=_response_thread_id,
                                        task_id=root_task_id,
                                        content=last_msg.content,
                                        agent_name="Inquirer",
                                    )
                                )

            logger.info(
                "stream_react_agent: completed React Agent stream for conversation {}",
                conversation_id,
            )

        except Exception as exc:
            logger.exception(
                f"stream_react_agent: execution failed for conversation {conversation_id}: {exc}"
            )
            # Emit error message
            yield await self.event_service.emit(
                self.event_service.factory.message_response_general(
                    event=StreamResponseEvent.MESSAGE_CHUNK,
                    conversation_id=conversation_id,
                    thread_id=_response_thread_id,
                    task_id=root_task_id,
                    content=f"⚠️ System Error: {str(exc)}",
                    agent_name="System",
                )
            )

    # ==================== Public API Methods ====================

    async def process_user_input(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """
        Stream responses for a user input, decoupled from the caller's lifetime.

        This function now spawns a background producer task that runs the
        planning/execution pipeline and emits responses. The async generator
        here simply consumes from a local queue. If the consumer disconnects,
        the background task continues, ensuring scheduled tasks and long-running
        plans proceed independently of the SSE connection.
        """
        # Per-invocation queue and active flag
        queue: asyncio.Queue[Optional[BaseResponse]] = asyncio.Queue()
        active = {"value": True}

        async def emit(item: Optional[BaseResponse]):
            # Drop emissions if the consumer has gone away
            if not active["value"]:
                return
            try:
                await queue.put(item)
            except Exception:
                # Never fail producer due to queue issues; just drop
                pass

        logger.info(
            "process_user_input: starting background session for conversation {}",
            user_input.meta.conversation_id,
        )
        # Start background producer
        asyncio.create_task(self._run_session(user_input, emit))

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        except asyncio.CancelledError:
            # Consumer cancelled; mark inactive so producer stops enqueuing
            active["value"] = False
            # Do not cancel producer; it should continue independently
            raise
        finally:
            # Mark inactive to stop further enqueues
            active["value"] = False
            # Best-effort: if producer already finished, nothing to do
            # We deliberately do not cancel the producer to keep execution alive

    # ==================== Private Helper Methods ====================

    async def _run_session(
        self,
        user_input: UserInput,
        emit: callable,
    ):
        """Background session runner that produces responses and emits them.

        It wraps the original processing pipeline and forwards each response to
        the provided emitter. Completion is signaled with a final None.
        """
        try:
            async for response in self._generate_responses(user_input):
                await emit(response)
        except Exception as e:
            # The underlying pipeline already emits system_failed + done, so this
            # path should be rare; still, don't crash the background task.
            logger.exception(
                f"Unhandled error in session runner for conversation {user_input.meta.conversation_id}: {e}"
            )
        finally:
            # Signal completion to the consumer (if any)
            try:
                await emit(None)
            except Exception:
                pass

    async def _generate_responses(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Generate responses for a user input (original pipeline extracted).

        This contains the previous body of process_user_input unchanged in
        behavior, yielding the same responses in the same order.
        """
        conversation_id = user_input.meta.conversation_id

        try:
            conversation, created = await self.conversation_service.ensure_conversation(
                user_id=user_input.meta.user_id,
                conversation_id=conversation_id,
                agent_name=user_input.target_agent_name,
            )

            if created:
                started = self.event_service.factory.conversation_started(
                    conversation_id=conversation_id
                )
                yield await self.event_service.emit(started)

            if conversation.status == ConversationStatus.REQUIRE_USER_INPUT:
                logger.info(
                    "_generate_responses: resuming conversation {} in REQUIRE_USER_INPUT",
                    conversation_id,
                )
                async for response in self._handle_conversation_continuation(
                    user_input
                ):
                    yield response
            else:
                logger.info(
                    "_generate_responses: handling new request for conversation {}",
                    conversation_id,
                )
                async for response in self._handle_new_request(user_input):
                    yield response

        except Exception as e:
            logger.exception(
                f"Error processing user input for conversation {conversation_id}"
            )
            failure = self.event_service.factory.system_failed(
                conversation_id, f"(Error) Error processing request: {str(e)}"
            )
            yield await self.event_service.emit(failure)
        finally:
            yield self.event_service.factory.done(conversation_id)

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
            failure = self.event_service.factory.system_failed(
                conversation_id,
                "No execution context found for this conversation. The conversation may have expired.",
            )
            yield await self.event_service.emit(failure)
            return

        context = self._execution_contexts[conversation_id]

        # Validate context integrity and user consistency
        if not self._validate_execution_context(context, user_id):
            failure = self.event_service.factory.system_failed(
                conversation_id,
                "Invalid execution context or user mismatch.",
            )
            yield await self.event_service.emit(failure)
            await self._cancel_execution(conversation_id)
            return

        thread_id = generate_thread_id()
        response = self.event_service.factory.thread_started(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_query=user_input.query,
        )
        yield await self.event_service.emit(response)

        # Provide user response and resume execution
        # If we are in an execution stage, store the pending response for resume
        context.add_metadata(pending_response=user_input.query)
        if self.plan_service.provide_user_response(conversation_id, user_input.query):
            await self.conversation_service.activate(conversation_id)
        context.thread_id = thread_id

        # Resume based on execution stage
        if context.stage == "planning":
            async for response in self._continue_planning(
                conversation_id, thread_id, context
            ):
                yield response
        # Resuming execution stage is not yet supported
        else:
            failure = self.event_service.factory.system_failed(
                conversation_id,
                "Resuming execution stage is not yet supported.",
            )
            yield await self.event_service.emit(failure)

    async def _handle_new_request(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Start planning and execution for a new user request.

        This creates a planner task (executed asynchronously) and yields
        streaming responses produced during planning and subsequent execution.
        """
        conversation_id = user_input.meta.conversation_id
        thread_id = generate_thread_id()
        response = self.event_service.factory.thread_started(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_query=user_input.query,
        )
        yield await self.event_service.emit(response)

        # 1) Super Agent triage phase (pre-planning) - skip if target agent is specified
        if user_input.target_agent_name == self.super_agent_service.name:
            async for response in self.stream_react_agent(user_input, thread_id):
                yield response

            return

        # 2) Planner phase (existing logic)
        # Create planning task with user input callback
        logger.info(
            "_handle_new_request: starting planner for conversation {}, thread {}",
            conversation_id,
            thread_id,
        )
        context_aware_callback = self._create_context_aware_callback(conversation_id)
        planning_task = self.plan_service.start_planning_task(
            user_input, thread_id, context_aware_callback
        )
        logger.info(
            "_handle_new_request: planner task started for conversation {}",
            conversation_id,
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
            self.plan_service.register_user_input(conversation_id, request)

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

        plan_task_id = generate_task_id()
        plan_tool_call_id = generate_uuid("tool_call")
        plan_tool_name = "generate_execution_plan"
        yield await self.event_service.emit(
            self.event_service.factory.tool_call(
                conversation_id,
                thread_id,
                task_id=plan_task_id,
                event=StreamResponseEvent.TOOL_CALL_STARTED,
                tool_call_id=plan_tool_call_id,
                tool_name=plan_tool_name,
            )
        )

        # Wait for planning completion or user input request
        logger.info(
            "_monitor_planning_task: monitoring planning task for conversation {}",
            conversation_id,
        )
        while not planning_task.done():
            if self.plan_service.has_pending_request(conversation_id):
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
                await self.conversation_service.require_user_input(conversation_id)
                prompt = self.plan_service.get_request_prompt(conversation_id) or ""
                response = self.event_service.factory.plan_require_user_input(
                    conversation_id,
                    thread_id,
                    prompt,
                )
                yield await self.event_service.emit(response)
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        logger.info(
            "_monitor_planning_task: planning completed for conversation {}; executing plan",
            conversation_id,
        )
        # Planning completed, execute plan
        plan: "ExecutionPlan" = await planning_task

        yield await self.event_service.emit(
            self.event_service.factory.tool_call(
                conversation_id,
                thread_id,
                task_id=plan_task_id,
                event=StreamResponseEvent.TOOL_CALL_COMPLETED,
                tool_call_id=plan_tool_call_id,
                tool_name=plan_tool_name,
                tool_result=(
                    f"Reason: {plan.guidance_message}"
                    if plan.guidance_message
                    else "Completed"
                ),
            )
        )

        # Set conversation title once if not set yet and a task title is available
        if getattr(plan, "tasks", None):
            first_title = getattr(plan.tasks[0], "title", None)
            await self._maybe_set_conversation_title(conversation_id, first_title)
        async for response in self.task_executor.execute_plan(plan, thread_id):
            yield response

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
            failure = self.event_service.factory.plan_failed(
                conversation_id,
                thread_id,
                "Invalid planning context - missing required data",
            )
            yield await self.event_service.emit(failure)
            await self._cancel_execution(conversation_id)
            return

        # Continue monitoring planning task
        while not planning_task.done():
            if self.plan_service.has_pending_request(conversation_id):
                # Still need more user input, send request
                prompt = self.plan_service.get_request_prompt(conversation_id) or ""
                # Ensure conversation is set to require user input again for repeated prompts
                await self.conversation_service.require_user_input(conversation_id)
                response = self.event_service.factory.plan_require_user_input(
                    conversation_id, thread_id, prompt
                )
                yield await self.event_service.emit(response)
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan and clean up context
        plan = await planning_task
        del self._execution_contexts[conversation_id]

        # If this conversation was just created (tracked in context), set its title once.
        if getattr(plan, "tasks", None):
            first_title = getattr(plan.tasks[0], "title", None)
            await self._maybe_set_conversation_title(conversation_id, first_title)

        async for response in self.task_executor.execute_plan(plan, thread_id):
            yield response

    async def _maybe_set_conversation_title(
        self, conversation_id: str, title: Optional[str]
    ):
        """Set conversation title once after creation when a task title is available.

        Only sets the title if:
        - title is provided and non-empty
        - the conversation exists and currently has no title
        """
        try:
            if not title or not str(title).strip():
                return
            conversation = await self.conversation_service.get_conversation(
                conversation_id
            )
            if not conversation:
                return
            # Avoid overwriting any existing title
            if conversation.title:
                return
            conversation.title = str(title).strip()
            # Persist via manager to avoid expanding ConversationService API
            await self.conversation_service.manager.update_conversation(conversation)
        except Exception:
            # Title setting is best-effort; failures shouldn't break flow
            logger.exception(f"Failed to set conversation title for {conversation_id}")

    async def _cancel_execution(self, conversation_id: str):
        """Cancel and clean up any execution resources associated with a
        conversation.

        This cancels the planner task (if present), removes the execution
        context and clears any pending user input. It also resets the
        conversation's status back to active.
        """
        if conversation_id in self._execution_contexts:
            context = self._execution_contexts.pop(conversation_id)
            planning_task = context.get_metadata(PLANNING_TASK)
            if planning_task and not planning_task.done():
                planning_task.cancel()

        self.plan_service.clear_pending_request(conversation_id)
        await self.conversation_service.activate(conversation_id)

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
