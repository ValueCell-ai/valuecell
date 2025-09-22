from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncGenerator, Callable, Optional

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


class StreamResponseEvent(str, Enum):
    MESSAGE_CHUNK = "message_chunk"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    REASONING = "reasoning"
    TASK_DONE = "task_done"
    TASK_FAILED = "task_failed"


class NotifyResponseEvent(str, Enum):
    MESSAGE = "message"
    TASK_DONE = "task_done"
    TASK_FAILED = "task_failed"


class StreamResponse(BaseModel):
    """Response model for streaming agent responses"""

    content: Optional[str] = Field(
        None,
        description="The content of the stream response, typically a chunk of data or message.",
    )
    event: StreamResponseEvent = Field(
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
    event: NotifyResponseEvent = Field(
        ...,
        description="The type of notification response",
    )


class ToolCallContent(BaseModel):
    tool_call_id: str = Field(..., description="Unique ID for the tool call")
    tool_name: str = Field(..., description="Name of the tool being called")
    tool_result: Optional[str] = Field(
        None,
        description="The content returned from the tool call, if any.",
    )


class ProcessMessageData(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID for this request")
    message_id: str = Field(..., description="Message ID for this request")
    content: str | ToolCallContent = Field(
        ..., description="Content of the message chunk"
    )


class ProcessMessage(BaseModel):
    """Chunk of a message, useful for streaming responses"""

    event: StreamResponseEvent | NotifyResponseEvent = Field(
        ..., description="The event type of the message chunk"
    )
    data: ProcessMessageData = Field(..., description="Content of the message chunk")


# TODO: keep only essential parameters
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
