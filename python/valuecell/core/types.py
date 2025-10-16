from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncGenerator, Callable, Dict, Literal, Optional, Union

from a2a.types import Task, TaskArtifactUpdateEvent, TaskStatusUpdateEvent
from pydantic import BaseModel, Field

from valuecell.utils.uuid import generate_item_id


class UserInputMetadata(BaseModel):
    """Metadata associated with user input"""

    conversation_id: Optional[str] = Field(
        None, description="Conversation ID for this request"
    )
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


class SystemResponseEvent(str, Enum):
    """Events related to system-level responses and status updates."""

    CONVERSATION_STARTED = "conversation_started"
    THREAD_STARTED = "thread_started"
    PLAN_REQUIRE_USER_INPUT = "plan_require_user_input"
    PLAN_FAILED = "plan_failed"
    SYSTEM_FAILED = "system_failed"
    DONE = "done"


class TaskStatusEvent(str, Enum):
    """Events related to task lifecycle status changes."""

    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"


class CommonResponseEvent(str, Enum):
    """Common response events shared across different response types."""

    COMPONENT_GENERATOR = "component_generator"


class StreamResponseEvent(str, Enum):
    """Events specific to streaming agent responses."""

    MESSAGE_CHUNK = "message_chunk"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    REASONING_STARTED = "reasoning_started"
    REASONING = "reasoning"
    REASONING_COMPLETED = "reasoning_completed"


class NotifyResponseEvent(str, Enum):
    """Events specific to notification agent responses."""

    MESSAGE = "message"


class StreamResponse(BaseModel):
    """Response model for streaming agent responses.

    Used by agents that stream progress, tool calls, reasoning, or
    component-generation updates. `event` determines how the response
    should be interpreted.
    """

    content: Optional[str] = Field(
        None,
        description="The content of the stream response, typically a chunk of data or message.",
    )
    event: StreamResponseEvent | TaskStatusEvent | CommonResponseEvent = Field(
        ...,
        description="The type of stream response, indicating its purpose or content nature.",
    )
    metadata: Optional[dict] = Field(
        None,
        description="Optional metadata providing additional context about the response",
    )


class NotifyResponse(BaseModel):
    """Response model for notification agent responses"""

    content: str = Field(
        ...,
        description="The content of the notification response",
    )
    event: NotifyResponseEvent | TaskStatusEvent | CommonResponseEvent = Field(
        ...,
        description="The type of notification response",
    )


class ToolCallPayload(BaseModel):
    """Payload describing a tool call made by an agent.

    Contains identifiers and optional result content produced by the tool.
    """

    tool_call_id: str = Field(..., description="Unique ID for the tool call")
    tool_name: str = Field(..., description="Name of the tool being called")
    tool_result: Optional[str] = Field(
        None,
        description="The content returned from the tool call, if any.",
    )


class BaseResponseDataPayload(BaseModel, ABC):
    """Base class for response data payloads."""

    content: Optional[str] = Field(None, description="The message content")


class ComponentGeneratorResponseDataPayload(BaseResponseDataPayload):
    """Payload for responses that generate UI components.

    `component_type` describes the kind of component produced.
    """

    component_type: str = Field(..., description="The component type")


class ComponentType(str, Enum):
    """Component type enumeration."""

    REPORT = "report"
    PROFILE = "profile"


class ReportComponentData(BaseModel):
    """Report component data payload."""

    title: str = Field(
        ..., description="The report title, used by UI to display the report title"
    )
    data: str = Field(..., description="The report data")
    url: Optional[str] = Field(None, description="The report URL")
    create_time: str = Field(
        ..., description="The report create time, UTC time, YYYY-MM-DD HH:MM:SS format"
    )


ResponsePayload = Union[
    BaseResponseDataPayload,
    ComponentGeneratorResponseDataPayload,
    ToolCallPayload,
]


ConversationItemEvent = Union[
    StreamResponseEvent,
    NotifyResponseEvent,
    SystemResponseEvent,
    CommonResponseEvent,
    TaskStatusEvent,
]


class Role(str, Enum):
    """Message role enumeration."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ConversationItem(BaseModel):
    """Message item structure for conversation history.

    Represents a single message/event within a conversation and stores
    identifiers, role, event type and payload.
    """

    item_id: str = Field(..., description="Unique message identifier")
    role: Role = Field(..., description="Role of the message sender")
    event: ConversationItemEvent = Field(..., description="Event type of the message")
    conversation_id: str = Field(
        ..., description="Conversation ID this message belongs to"
    )
    thread_id: Optional[str] = Field(None, description="Thread ID if part of a thread")
    task_id: Optional[str] = Field(
        None, description="Task ID if associated with a task"
    )
    payload: str = Field(..., description="The actual message payload")


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
    payload: Optional[ResponsePayload] = Field(
        None, description="The message data payload"
    )
    role: Role = Field(..., description="The role of the message sender")
    item_id: str = Field(default_factory=generate_item_id)


class BaseResponse(BaseModel, ABC):
    """Top-level response envelope used for all events.

    Subclasses narrow the `event` literal and `data` payload for specific
    response kinds (message, task updates, system events, etc.).
    """

    event: ConversationItemEvent = Field(
        ..., description="The event type of the response"
    )
    data: UnifiedResponseData = Field(
        ..., description="The data payload of the response"
    )


class ConversationStartedResponse(BaseResponse):
    """Response indicating a conversation has started."""

    event: Literal[SystemResponseEvent.CONVERSATION_STARTED] = Field(
        SystemResponseEvent.CONVERSATION_STARTED,
        description="The event type of the response",
    )


class ThreadStartedResponse(BaseResponse):
    """Response indicating a thread has started."""

    event: Literal[SystemResponseEvent.THREAD_STARTED] = Field(
        SystemResponseEvent.THREAD_STARTED,
        description="The event type of the response",
    )


class PlanRequireUserInputResponse(BaseResponse):
    """Response indicating the execution plan requires user input."""

    event: Literal[SystemResponseEvent.PLAN_REQUIRE_USER_INPUT] = Field(
        SystemResponseEvent.PLAN_REQUIRE_USER_INPUT,
        description="The event type of the response",
    )
    data: UnifiedResponseData = Field(..., description="The plan data payload")


class MessageResponse(BaseResponse):
    """Response containing a message payload (streamed or notified)."""

    event: Literal[
        StreamResponseEvent.MESSAGE_CHUNK,
        NotifyResponseEvent.MESSAGE,
    ] = Field(..., description="The event type of the response")
    data: UnifiedResponseData = Field(..., description="The complete message content")


class ComponentGeneratorResponse(BaseResponse):
    """Response that carries component generation data for UI rendering."""

    event: Literal[CommonResponseEvent.COMPONENT_GENERATOR] = Field(
        CommonResponseEvent.COMPONENT_GENERATOR,
        description="The event type of the response",
    )
    data: UnifiedResponseData = Field(..., description="The component generator data")


class ToolCallResponse(BaseResponse):
    """Response representing tool call lifecycle events."""

    event: Literal[
        StreamResponseEvent.TOOL_CALL_STARTED, StreamResponseEvent.TOOL_CALL_COMPLETED
    ] = Field(
        ...,
        description="The event type of the response",
    )
    data: UnifiedResponseData = Field(..., description="The task data payload")


class ReasoningResponse(BaseResponse):
    """Response containing intermediate reasoning events from the agent."""

    event: Literal[
        StreamResponseEvent.REASONING_STARTED,
        StreamResponseEvent.REASONING,
        StreamResponseEvent.REASONING_COMPLETED,
    ] = Field(..., description="The event type of the response")
    data: UnifiedResponseData = Field(..., description="The reasoning message content")


class DoneResponse(BaseResponse):
    """Response indicating a thread or conversation is done."""

    event: Literal[SystemResponseEvent.DONE] = Field(
        SystemResponseEvent.DONE, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The thread data payload")


class PlanFailedResponse(BaseResponse):
    """Response indicating a plan execution failure."""

    event: Literal[SystemResponseEvent.PLAN_FAILED] = Field(
        SystemResponseEvent.PLAN_FAILED, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The plan data payload")


class TaskStartedResponse(BaseResponse):
    """Response indicating a task has been started."""

    event: Literal[TaskStatusEvent.TASK_STARTED] = Field(
        TaskStatusEvent.TASK_STARTED, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The task data payload")


class TaskFailedResponse(BaseResponse):
    """Response indicating a task has failed."""

    event: Literal[TaskStatusEvent.TASK_FAILED] = Field(
        TaskStatusEvent.TASK_FAILED, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The task data payload")


class TaskCompletedResponse(BaseResponse):
    """Response indicating a task has completed successfully."""

    event: Literal[TaskStatusEvent.TASK_COMPLETED] = Field(
        TaskStatusEvent.TASK_COMPLETED, description="The event type of the response"
    )
    data: UnifiedResponseData = Field(..., description="The task data payload")


class SystemFailedResponse(BaseResponse):
    """Response indicating a system-level failure for the conversation."""

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
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        """
        Process user queries and return streaming responses (user-initiated)

        Args:
            query: User query content
            conversation_id: Conversation ID
            task_id: Task ID
            dependencies: Optional dependencies containing language, timezone, and other context

        Yields:
            StreamResponse: Stream response containing content and completion status
        """
        raise NotImplementedError

    async def notify(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[NotifyResponse, None]:
        """
        Send proactive notifications to subscribed users (agent-initiated)

        Args:
            query: User query content, can be empty for some agents
            conversation_id: Conversation ID for the notification
            user_id: Target user ID for the notification
            dependencies: Optional dependencies containing language, timezone, and other context

        Yields:
            NotifyResponse: Notification content and status
        """
        raise NotImplementedError


# Message response type for agent communication
RemoteAgentResponse = tuple[
    Task, Optional[TaskStatusUpdateEvent | TaskArtifactUpdateEvent]
]

NotificationCallbackType = Callable[[Task], None]
