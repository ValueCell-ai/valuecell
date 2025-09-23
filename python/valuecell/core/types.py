from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncGenerator, Callable, Literal, Optional, Union

from a2a.types import Task, TaskArtifactUpdateEvent, TaskStatusUpdateEvent
from pydantic import BaseModel, Field


class UserInputMetadata(BaseModel):
    """Metadata associated with user input"""

    session_id: Optional[str] = Field(None, description="Session ID for this request")
    user_id: str = Field(..., description="User ID who made this request")


class UserInput(BaseModel):
    """Unified abstraction for user input containing all necessary parameters"""

    query: str = Field(..., description="The actual user input text")
    desired_agent_name: Optional[str] = Field(
        None, description="Specific agent name to use for processing this input"
    )
    meta: UserInputMetadata = Field(
        ..., description="Metadata associated with the user input"
    )

    class Config:
        """Pydantic configuration"""

        frozen = False
        extra = "forbid"

    def has_desired_agent(self) -> bool:
        """Check if a specific agent is desired"""
        return self.desired_agent_name is not None

    def get_desired_agent(self) -> Optional[str]:
        """Get the desired agent name"""
        return self.desired_agent_name

    def set_desired_agent(self, agent_name: str) -> None:
        """Set the desired agent name"""
        self.desired_agent_name = agent_name

    def clear_desired_agent(self) -> None:
        """Clear the desired agent name"""
        self.desired_agent_name = None


class SystemResponseEvent(str, Enum):
    CONVERSATION_STARTED = "conversation_started"
    THREAD_STARTED = "thread_started"
    PLAN_REQUIRE_USER_INPUT = "plan_require_user_input"
    PLAN_FAILED = "plan_failed"
    TASK_FAILED = "task_failed"
    SYSTEM_FAILED = "system_failed"
    DONE = "done"


class _TaskResponseEvent(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_CANCELLED = "task_cancelled"


class StreamResponseEvent(str, Enum):
    MESSAGE_CHUNK = "message_chunk"
    COMPONENT_GENERATOR = "component_generator"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    REASONING_STARTED = "reasoning_started"
    REASONING = "reasoning"
    REASONING_COMPLETED = "reasoning_completed"


class NotifyResponseEvent(str, Enum):
    MESSAGE = "message"


class StreamResponse(BaseModel):
    """Response model for streaming agent responses"""

    content: Optional[str] = Field(
        None,
        description="The content of the stream response, typically a chunk of data or message.",
    )
    event: StreamResponseEvent | _TaskResponseEvent = Field(
        ...,
        description="The type of stream response, indicating its purpose or content nature.",
    )
    metadata: Optional[dict] = Field(
        None,
        description="Optional metadata providing additional context about the response",
    )
    subtask_id: Optional[str] = Field(
        None,
        description="Optional subtask ID if the response is related to a specific subtask",
    )


class NotifyResponse(BaseModel):
    """Response model for notification agent responses"""

    content: str = Field(
        ...,
        description="The content of the notification response",
    )
    event: NotifyResponseEvent | _TaskResponseEvent = Field(
        ...,
        description="The type of notification response",
    )


class ToolCallPayload(BaseModel):
    tool_call_id: str = Field(..., description="Unique ID for the tool call")
    tool_name: str = Field(..., description="Name of the tool being called")
    tool_result: Optional[str] = Field(
        None,
        description="The content returned from the tool call, if any.",
    )


class BaseResponseDataPayload(BaseModel, ABC):
    content: Optional[str] = Field(None, description="The message content")


class ComponentGeneratorResponseDataPayload(BaseResponseDataPayload):
    component_type: str = Field(..., description="The component type")


ResponsePayload = Union[
    BaseResponseDataPayload,
    ComponentGeneratorResponseDataPayload,
    ToolCallPayload,
]


class UnifiedResponseData(BaseModel):
    """Unified response data structure with optional hierarchy fields.

    Field names are preserved to maintain JSON compatibility when using
    model_dump(exclude_none=True).
    """

    conversation_id: str = Field(..., description="Unique ID for the conversation")
    thread_id: Optional[str] = Field(
        None, description="Unique ID for the message thread"
    )
    task_id: Optional[str] = Field(None, description="Unique ID for the task")
    subtask_id: Optional[str] = Field(
        None, description="Unique ID for the subtask, if any"
    )
    payload: Optional[ResponsePayload] = Field(
        None, description="The message data payload"
    )


class BaseResponse(BaseModel, ABC):
    """Top-level response envelope used for all events."""

    event: StreamResponseEvent | NotifyResponseEvent | SystemResponseEvent = Field(
        ..., description="The event type of the response"
    )
    data: UnifiedResponseData = Field(
        ..., description="The data payload of the response"
    )


class ConversationStartedResponse(BaseResponse):
    event: Literal[SystemResponseEvent.CONVERSATION_STARTED] = Field(
        SystemResponseEvent.CONVERSATION_STARTED,
        description="The event type of the response",
    )


class ThreadStartedResponse(BaseResponse):
    event: Literal[SystemResponseEvent.THREAD_STARTED] = Field(
        SystemResponseEvent.THREAD_STARTED,
        description="The event type of the response",
    )


class PlanRequireUserInputResponse(BaseResponse):
    event: Literal[SystemResponseEvent.PLAN_REQUIRE_USER_INPUT] = Field(
        SystemResponseEvent.PLAN_REQUIRE_USER_INPUT,
        description="The event type of the response",
    )
    data: UnifiedResponseData = Field(..., description="The plan data payload")


class MessageResponse(BaseResponse):
    event: Literal[
        StreamResponseEvent.MESSAGE_CHUNK,
        NotifyResponseEvent.MESSAGE,
    ] = Field(..., description="The event type of the response")
    data: UnifiedResponseData = Field(..., description="The complete message content")


class ComponentGeneratorResponse(BaseResponse):
    event: Literal[StreamResponseEvent.COMPONENT_GENERATOR] = Field(
        StreamResponseEvent.COMPONENT_GENERATOR
    )
    data: UnifiedResponseData = Field(..., description="The component generator data")


class ToolCallResponse(BaseResponse):
    event: Literal[
        StreamResponseEvent.TOOL_CALL_STARTED, StreamResponseEvent.TOOL_CALL_COMPLETED
    ] = Field(
        ...,
        description="The event type of the response",
    )
    data: UnifiedResponseData = Field(..., description="The task data payload")


class ReasoningResponse(BaseResponse):
    event: Literal[
        StreamResponseEvent.REASONING_STARTED,
        StreamResponseEvent.REASONING,
        StreamResponseEvent.REASONING_COMPLETED,
    ] = Field(..., description="The event type of the response")
    data: UnifiedResponseData = Field(..., description="The reasoning message content")


class DoneResponse(BaseResponse):
    event: Literal[SystemResponseEvent.DONE] = Field(
        SystemResponseEvent.DONE, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The thread data payload")


class PlanFailedResponse(BaseResponse):
    event: Literal[SystemResponseEvent.PLAN_FAILED] = Field(
        SystemResponseEvent.PLAN_FAILED, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The plan data payload")


class TaskFailedResponse(BaseResponse):
    event: Literal[SystemResponseEvent.TASK_FAILED] = Field(
        SystemResponseEvent.TASK_FAILED, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The task data payload")


class TaskCompletedResponse(BaseResponse):
    event: Literal[_TaskResponseEvent.TASK_COMPLETED] = Field(
        _TaskResponseEvent.TASK_COMPLETED, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The task data payload")


class SystemFailedResponse(BaseResponse):
    event: Literal[SystemResponseEvent.SYSTEM_FAILED] = Field(
        SystemResponseEvent.SYSTEM_FAILED, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The conversation data payload")


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """

    @abstractmethod
    async def stream(
        self, query: str, session_id: str, task_id: str
    ) -> AsyncGenerator[StreamResponse, None]:
        """
        Process user queries and return streaming responses (user-initiated)

        Args:
            query: User query content
            session_id: Session ID
            task_id: Task ID

        Yields:
            StreamResponse: Stream response containing content and completion status
        """
        raise NotImplementedError

    async def notify(
        self, query: str, session_id: str, task_id: str
    ) -> AsyncGenerator[NotifyResponse, None]:
        """
        Send proactive notifications to subscribed users (agent-initiated)

        Args:
            query: User query content, can be empty for some agents
            session_id: Session ID for the notification
            user_id: Target user ID for the notification

        Yields:
            NotifyResponse: Notification content and status
        """
        raise NotImplementedError


# Message response type for agent communication
RemoteAgentResponse = tuple[
    Task, Optional[TaskStatusUpdateEvent | TaskArtifactUpdateEvent]
]

NotificationCallbackType = Callable[[Task], None]
