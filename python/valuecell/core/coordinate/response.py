from typing import Optional

from typing_extensions import Literal
from valuecell.core.types import (
    BaseResponseDataPayload,
    CommonResponseEvent,
    ComponentGeneratorResponse,
    ComponentGeneratorResponseDataPayload,
    ConversationItem,
    ConversationStartedResponse,
    DoneResponse,
    MessageResponse,
    NotifyResponseEvent,
    PlanFailedResponse,
    PlanRequireUserInputResponse,
    ReasoningResponse,
    Role,
    StreamResponseEvent,
    SystemFailedResponse,
    SystemResponseEvent,
    TaskCompletedResponse,
    TaskFailedResponse,
    TaskStatusEvent,
    ThreadStartedResponse,
    ToolCallPayload,
    ToolCallResponse,
    UnifiedResponseData,
)
from valuecell.utils.uuid import generate_item_id, generate_uuid


class ResponseFactory:
    def from_conversation_item(self, item: ConversationItem):
        """Reconstruct a BaseResponse from a persisted ConversationItem.

        - Maps the stored event to the appropriate Response subtype
        - Parses payload JSON back into the right payload model when possible
        - Preserves the original item_id so callers can correlate history items
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

        # Base UnifiedResponseData builder
        def make_data(payload=None):
            return UnifiedResponseData(
                conversation_id=item.conversation_id,
                thread_id=item.thread_id,
                task_id=item.task_id,
                payload=payload,
                role=role,
                item_id=item.item_id,
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
        return ConversationStartedResponse(
            data=UnifiedResponseData(conversation_id=conversation_id, role=Role.SYSTEM)
        )

    def thread_started(
        self, conversation_id: str, thread_id: str, user_query: str
    ) -> ThreadStartedResponse:
        return ThreadStartedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=generate_uuid("ask"),
                payload=BaseResponseDataPayload(content=user_query),
                role=Role.USER,
            )
        )

    def system_failed(self, conversation_id: str, content: str) -> SystemFailedResponse:
        return SystemFailedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                payload=BaseResponseDataPayload(content=content),
                role=Role.SYSTEM,
            )
        )

    def done(self, conversation_id: str, thread_id: str) -> DoneResponse:
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
    ) -> TaskFailedResponse:
        return TaskFailedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=BaseResponseDataPayload(content=content),
                role=Role.AGENT,
            )
        )

    def task_completed(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
    ) -> TaskCompletedResponse:
        return TaskCompletedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                role=Role.AGENT,
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
    ) -> ToolCallResponse:
        return ToolCallResponse(
            event=event,
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=ToolCallPayload(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    tool_result=tool_result,
                ),
                role=Role.AGENT,
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
    ) -> MessageResponse:
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
    ) -> ReasoningResponse:
        return ReasoningResponse(
            event=event,
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                payload=(BaseResponseDataPayload(content=content) if content else None),
                role=Role.AGENT,
            ),
        )

    def component_generator(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        content: str,
        component_type: str,
    ) -> ComponentGeneratorResponse:
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
            ),
        )
