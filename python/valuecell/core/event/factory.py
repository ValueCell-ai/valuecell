from typing import Optional

from typing_extensions import Literal

from valuecell.core.task.models import Task
from valuecell.core.types import (
    BaseResponseDataPayload,
    CommonResponseEvent,
    ComponentGeneratorResponse,
    ComponentGeneratorResponseDataPayload,
    ComponentType,
    ConversationItem,
    ConversationStartedResponse,
    DoneResponse,
    MessageResponse,
    NotifyResponseEvent,
    PlanFailedResponse,
    PlanRequireUserInputResponse,
    ReasoningResponse,
    Role,
    ScheduledTaskComponentContent,
    StreamResponseEvent,
    SystemFailedResponse,
    SystemResponseEvent,
    TaskCompletedResponse,
    TaskFailedResponse,
    TaskStartedResponse,
    TaskStatusEvent,
    ThreadStartedResponse,
    ToolCallPayload,
    ToolCallResponse,
    UnifiedResponseData,
)
from valuecell.utils.uuid import generate_item_id, generate_uuid


def _format_tool_result_for_frontend(result: str | None) -> str | None:
    """Format tool result as JSON array for frontend rendering.

    The frontend tool-call-renderer expects tool_result to be a JSON array
    of objects with 'content' field, e.g., '[{"content": "result text"}]'.

    If the result is already in this format, return it unchanged.

    Args:
        result: Raw tool result string.

    Returns:
        JSON-formatted string compatible with frontend renderer, or None if empty.
    """
    import json

    if not result:
        return result

    # Check if already in expected format: [{"content": ...}]
    try:
        parsed = json.loads(result)
        if (
            isinstance(parsed, list)
            and len(parsed) > 0
            and isinstance(parsed[0], dict)
            and "content" in parsed[0]
        ):
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    return json.dumps([{"content": result}])


class ResponseFactory:
    def from_conversation_item(self, item: ConversationItem):
        """Reconstruct a BaseResponse from a persisted ConversationItem.

        This method maps the stored event enum to the appropriate response
        subtype, attempts to parse the stored payload JSON into the
        corresponding payload model, and preserves the original `item_id` so
        callers can correlate the reconstructed response with the persisted
        conversation item.

        Args:
            item: The persisted ConversationItem to convert.

        Returns:
            An instance of a `BaseResponse` subtype (e.g., MessageResponse,
            ReasoningResponse, ThreadStartedResponse) corresponding to the
            stored event.
        """

        # Coerce enums that may have been persisted as strings
        ev = item.event
        if isinstance(ev, str):
            for enum_cls in (
                SystemResponseEvent,
                StreamResponseEvent,
                NotifyResponseEvent,
                CommonResponseEvent,
                TaskStatusEvent,
            ):
                try:
                    ev = enum_cls(ev)  # type: ignore[arg-type]
                    break
                except Exception:
                    continue

        role = item.role
        if isinstance(role, str):
            try:
                role = Role(role)
            except Exception:
                role = Role.AGENT

        # Helpers for payload parsing
        def parse_payload_as(model_cls):
            raw = item.payload
            if raw is None:
                return None
            try:
                return model_cls.model_validate_json(raw)
            except Exception:
                # Fallback to plain text payload
                try:
                    return BaseResponseDataPayload(content=str(raw))
                except Exception:
                    return None

        # Parse metadata
        def parse_metadata():
            raw_metadata = item.metadata
            if not raw_metadata:
                return None
            try:
                import json

                return json.loads(raw_metadata)
            except Exception:
                return None

        # Base UnifiedResponseData builder
        def make_data(payload=None):
            return UnifiedResponseData(
                conversation_id=item.conversation_id,
                thread_id=item.thread_id,
                task_id=item.task_id,
                payload=payload,
                role=role,
                item_id=item.item_id,
                agent_name=item.agent_name,
                metadata=parse_metadata(),
            )

        # ----- System-level events -----
        if ev == SystemResponseEvent.THREAD_STARTED:
            payload = parse_payload_as(BaseResponseDataPayload)
            return ThreadStartedResponse(data=make_data(payload))

        if ev == SystemResponseEvent.PLAN_REQUIRE_USER_INPUT:
            payload = parse_payload_as(BaseResponseDataPayload)
            return PlanRequireUserInputResponse(data=make_data(payload))

        # ----- Stream/notify/common events -----
        if ev == StreamResponseEvent.MESSAGE_CHUNK:
            payload = parse_payload_as(BaseResponseDataPayload)
            return MessageResponse(
                event=StreamResponseEvent.MESSAGE_CHUNK, data=make_data(payload)
            )

        if ev == NotifyResponseEvent.MESSAGE:
            payload = parse_payload_as(BaseResponseDataPayload)
            return MessageResponse(
                event=NotifyResponseEvent.MESSAGE, data=make_data(payload)
            )

        if ev in (
            StreamResponseEvent.REASONING,
            StreamResponseEvent.REASONING_STARTED,
            StreamResponseEvent.REASONING_COMPLETED,
        ):
            payload = parse_payload_as(BaseResponseDataPayload)
            # ReasoningResponse accepts optional payload
            return ReasoningResponse(event=ev, data=make_data(payload))

        if ev == CommonResponseEvent.COMPONENT_GENERATOR:
            payload = parse_payload_as(ComponentGeneratorResponseDataPayload)
            return ComponentGeneratorResponse(data=make_data(payload))

        if ev in (
            StreamResponseEvent.TOOL_CALL_STARTED,
            StreamResponseEvent.TOOL_CALL_COMPLETED,
        ):
            payload = parse_payload_as(ToolCallPayload)
            return ToolCallResponse(event=ev, data=make_data(payload))

        raise ValueError(
            f"Unsupported event type: {ev} when processing conversation item."
        )

    def conversation_started(self, conversation_id: str) -> ConversationStartedResponse:
        """Build a `ConversationStartedResponse` for a given conversation id.

        Args:
            conversation_id: The id of the conversation that started.

        Returns:
            ConversationStartedResponse with system role and the conversation id.
        """
        return ConversationStartedResponse(
            data=UnifiedResponseData(conversation_id=conversation_id, role=Role.SYSTEM)
        )

    def thread_started(
        self,
        conversation_id: str,
        thread_id: str,
        user_query: str,
        agent_name: Optional[str] = None,
    ) -> ThreadStartedResponse:
        """Create a `ThreadStartedResponse` for a new conversational thread.

        Args:
            conversation_id: Conversation the thread belongs to.
            thread_id: Newly generated thread identifier.
            user_query: The user's original query that started this thread.
            agent_name: Name of the agent handling this thread.

        Returns:
            ThreadStartedResponse populated with a synthetic ask task id and
            the user's query as payload.
        """
        return ThreadStartedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=generate_uuid("ask"),
                payload=BaseResponseDataPayload(content=user_query),
                role=Role.USER,
                agent_name=agent_name,
            )
        )

    def system_failed(self, conversation_id: str, content: str) -> SystemFailedResponse:
        """Return a system-level failure response.

        Args:
            conversation_id: Conversation where the failure occurred.
            content: Human-readable failure message.

        Returns:
            SystemFailedResponse with the provided content.
        """
        return SystemFailedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                payload=BaseResponseDataPayload(content=content),
                role=Role.SYSTEM,
            )
        )

    def done(
        self, conversation_id: str, thread_id: Optional[str] = None
    ) -> DoneResponse:
        """Return a terminal DoneResponse for the conversation/thread.

        Args:
            conversation_id: The conversation id.
            thread_id: Optional thread id this done message corresponds to.

        Returns:
            A DoneResponse indicating the end of a response stream.
        """
        return DoneResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                role=Role.SYSTEM,
            )
        )

    def plan_require_user_input(
        self, conversation_id: str, thread_id: str, content: str
    ) -> PlanRequireUserInputResponse:
        """Build a PlanRequireUserInputResponse prompting the user for info.

        Args:
            conversation_id: Conversation id awaiting user input.
            thread_id: Thread id for the pending prompt.
            content: Prompt text to present to the user.

        Returns:
            PlanRequireUserInputResponse populated with the prompt.
        """
        return PlanRequireUserInputResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                payload=BaseResponseDataPayload(content=content),
                role=Role.SYSTEM,
            )
        )

    def plan_failed(
        self, conversation_id: str, thread_id: str, content: str
    ) -> PlanFailedResponse:
        """Return a PlanFailedResponse describing why planning failed.

        Args:
            conversation_id: Conversation the failed plan belongs to.
            thread_id: Thread id associated with the plan.
            content: Human-readable reason for failure.

        Returns:
            PlanFailedResponse with the provided reason.
        """
        return PlanFailedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                payload=BaseResponseDataPayload(content=content),
                role=Role.SYSTEM,
            )
        )

    def task_failed(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        content: str,
        agent_name: Optional[str] = None,
    ) -> TaskFailedResponse:
        """Create a TaskFailedResponse for a failed task execution.

        Args:
            conversation_id: Conversation the task belongs to.
            thread_id: Thread id the task was running in.
            task_id: Identifier of the failed task.
            content: Failure message or error details.

        Returns:
            TaskFailedResponse populated with failure details.
        """
        return TaskFailedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=BaseResponseDataPayload(content=content),
                role=Role.AGENT,
                agent_name=agent_name,
            )
        )

    def task_started(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        agent_name: Optional[str] = None,
    ) -> TaskStartedResponse:
        """Return a TaskStartedResponse indicating a task has begun execution.

        Args:
            conversation_id: Conversation id for the task.
            thread_id: Thread id where the task runs.
            task_id: The task identifier.

        Returns:
            TaskStartedResponse with agent role.
        """
        return TaskStartedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                role=Role.AGENT,
                agent_name=agent_name,
            ),
        )

    def task_completed(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        agent_name: Optional[str] = None,
    ) -> TaskCompletedResponse:
        """Create a TaskCompletedResponse signalling successful completion.

        Args:
            conversation_id: Conversation id for the task.
            thread_id: Thread id where the task ran.
            task_id: The completed task identifier.

        Returns:
            TaskCompletedResponse with agent role.
        """
        return TaskCompletedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                role=Role.AGENT,
                agent_name=agent_name,
            ),
        )

    def tool_call(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        event: Literal[
            StreamResponseEvent.TOOL_CALL_STARTED,
            StreamResponseEvent.TOOL_CALL_COMPLETED,
        ],
        tool_call_id: str,
        tool_name: str,
        tool_result: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> ToolCallResponse:
        """Build a ToolCallResponse representing a tool invocation/result.

        Args:
            conversation_id: Conversation id.
            thread_id: Thread id.
            task_id: Task id associated with the tool call.
            event: The tool call event enum (started/completed).
            tool_call_id: Identifier for this tool call.
            tool_name: Name of the tool invoked.
            tool_result: Optional textual result returned by the tool.

        Returns:
            ToolCallResponse containing a ToolCallPayload.
        """
        # Format tool_result for frontend when event is TOOL_CALL_COMPLETED
        formatted_result = (
            _format_tool_result_for_frontend(tool_result)
            if event == StreamResponseEvent.TOOL_CALL_COMPLETED
            else tool_result
        )
        return ToolCallResponse(
            event=event,
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=ToolCallPayload(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    tool_result=formatted_result,
                ),
                role=Role.AGENT,
                agent_name=agent_name,
                item_id=tool_call_id,
            ),
        )

    def message_response_general(
        self,
        event: Literal[StreamResponseEvent.MESSAGE_CHUNK, NotifyResponseEvent.MESSAGE],
        conversation_id: str,
        thread_id: str,
        task_id: str,
        content: str,
        item_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> MessageResponse:
        """Create a generic message response used for both stream and notify.

        Args:
            event: Either StreamResponseEvent.MESSAGE_CHUNK or
                NotifyResponseEvent.MESSAGE.
            conversation_id: Conversation id.
            thread_id: Thread id.
            task_id: Task id.
            content: Textual content of the message.
            item_id: Optional stable paragraph/item id; generated if omitted.

        Returns:
            MessageResponse containing the provided content and meta.
        """
        return MessageResponse(
            event=event,
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=BaseResponseDataPayload(
                    content=content,
                ),
                role=Role.AGENT,
                item_id=item_id or generate_item_id(),
                agent_name=agent_name,
            ),
        )

    def reasoning(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        event: Literal[
            StreamResponseEvent.REASONING,
            StreamResponseEvent.REASONING_STARTED,
            StreamResponseEvent.REASONING_COMPLETED,
        ],
        content: Optional[str] = None,
        agent_name: Optional[str] = None,
        item_id: Optional[str] = None,
    ) -> ReasoningResponse:
        """Build a reasoning response used to convey model chain-of-thought.

        Args:
            conversation_id: Conversation id.
            thread_id: Thread id.
            task_id: Task id.
            event: One of the reasoning-related stream events.
            content: Optional textual reasoning content.
            agent_name: Name of the agent generating the reasoning.
            item_id: Optional stable item id for correlating reasoning chunks.

        Returns:
            ReasoningResponse with optional payload.
        """
        return ReasoningResponse(
            event=event,
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=(BaseResponseDataPayload(content=content) if content else None),
                role=Role.AGENT,
                agent_name=agent_name,
                item_id=item_id or generate_item_id(),
            ),
        )

    def component_generator(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        content: str,
        component_type: str,
        component_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ComponentGeneratorResponse:
        """Create a ComponentGeneratorResponse for UI component generation.

        Args:
            conversation_id: Conversation id.
            thread_id: Thread id.
            task_id: Task id.
            content: Serialized component content (e.g., markup or json).
            component_type: Free-form type string for the generated component.
            item_id: Optional stable paragraph/item id; generated if omitted.
            component_id: Optional component id that overrides item_id for replace behavior.

        Returns:
            ComponentGeneratorResponse wrapping the payload.
        """
        return ComponentGeneratorResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=ComponentGeneratorResponseDataPayload(
                    content=content,
                    component_type=component_type,
                ),
                role=Role.AGENT,
                item_id=component_id or generate_item_id(),
                agent_name=agent_name,
                metadata=metadata,
            ),
        )

    def schedule_task_controller_component(
        self,
        conversation_id: str,
        thread_id: str,
        task: Task,
    ) -> ComponentGeneratorResponse:
        """Create a ComponentGeneratorResponse for a task controller component.

        Args:
            conversation_id: Conversation id.
            thread_id: Thread id.
            task_id: Task id.
            task_title: Title of the scheduled task.
            content: Serialized component content (e.g., markup or json).
            agent_name: Name of the agent generating the component.

        Returns:
            ComponentGeneratorResponse wrapping the payload.
        """
        return self.component_generator(
            conversation_id=conversation_id,
            thread_id=thread_id,
            task_id=task.task_id,
            content=ScheduledTaskComponentContent(
                task_id=task.task_id,
                task_title=task.title,
                task_status=task.status.value,
            ).model_dump_json(exclude_none=True),
            component_type=ComponentType.SCHEDULED_TASK_CONTROLLER.value,
            agent_name=task.agent_name,
            metadata={
                "task_title": task.title,
            },
        )

    def schedule_task_result_component(
        self,
        task: Task,
        content: str,
    ) -> ComponentGeneratorResponse:
        """Create a ComponentGeneratorResponse for a task result component.

        Args:
            task: The Task instance.
            result_content: Serialized content representing the task result.

        Returns:
            ComponentGeneratorResponse wrapping the payload.
        """
        return self.component_generator(
            conversation_id=task.conversation_id,
            thread_id=task.thread_id,
            task_id=task.task_id,
            content=content,
            component_type=ComponentType.SCHEDULED_TASK_RESULT.value,
            agent_name=task.agent_name,
            metadata={
                "task_title": task.title,
            },
        )
