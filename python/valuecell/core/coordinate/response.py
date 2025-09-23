from typing import Optional

from typing_extensions import Literal
from valuecell.core.types import (
    BaseResponseDataPayload,
    ComponentGeneratorResponse,
    ComponentGeneratorResponseDataPayload,
    ConversationStartedResponse,
    DoneResponse,
    MessageResponse,
    NotifyResponseEvent,
    PlanFailedResponse,
    PlanRequireUserInputResponse,
    ReasoningResponse,
    StreamResponseEvent,
    SystemFailedResponse,
    TaskCompletedResponse,
    TaskFailedResponse,
    ThreadStartedResponse,
    ToolCallPayload,
    ToolCallResponse,
    UnifiedResponseData,
)


class ResponseFactory:
    def conversation_started(self, conversation_id: str) -> ConversationStartedResponse:
        return ConversationStartedResponse(
            data=UnifiedResponseData(conversation_id=conversation_id)
        )

    def thread_started(
        self, conversation_id: str, thread_id: str
    ) -> ThreadStartedResponse:
        return ThreadStartedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id, thread_id=thread_id
            )
        )

    def system_failed(self, conversation_id: str, content: str) -> SystemFailedResponse:
        return SystemFailedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                payload=BaseResponseDataPayload(content=content),
            )
        )

    def done(self, conversation_id: str, thread_id: str) -> DoneResponse:
        return DoneResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
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
            )
        )

    def task_failed(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        subtask_id: str | None,
        content: str,
    ) -> TaskFailedResponse:
        return TaskFailedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                subtask_id=subtask_id,
                payload=BaseResponseDataPayload(content=content),
            )
        )

    def task_completed(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        subtask_id: str | None,
    ) -> TaskCompletedResponse:
        return TaskCompletedResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                subtask_id=subtask_id,
            ),
        )

    def tool_call(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        subtask_id: str,
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
                subtask_id=subtask_id,
                payload=ToolCallPayload(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    tool_result=tool_result,
                ),
            ),
        )

    def message_response_general(
        self,
        event: Literal[StreamResponseEvent.MESSAGE_CHUNK, NotifyResponseEvent.MESSAGE],
        conversation_id: str,
        thread_id: str,
        task_id: str,
        subtask_id: str,
        content: str,
    ) -> MessageResponse:
        return MessageResponse(
            event=event,
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                subtask_id=subtask_id,
                payload=BaseResponseDataPayload(content=content),
            ),
        )

    def reasoning(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        subtask_id: str,
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
                subtask_id=subtask_id,
                payload=BaseResponseDataPayload(content=content) if content else None,
            ),
        )

    def component_generator(
        self,
        conversation_id: str,
        thread_id: str,
        task_id: str,
        subtask_id: str,
        content: str,
        component_type: str,
    ) -> ComponentGeneratorResponse:
        return ComponentGeneratorResponse(
            data=UnifiedResponseData(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                subtask_id=subtask_id,
                payload=ComponentGeneratorResponseDataPayload(
                    content=content,
                    component_type=component_type,
                ),
            ),
        )
