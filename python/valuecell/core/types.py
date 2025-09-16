from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncGenerator, Callable, Optional

from a2a.types import Task, TaskArtifactUpdateEvent, TaskStatusUpdateEvent
from pydantic import BaseModel, Field


class UserInputMetadata(BaseModel):
    """Metadata associated with user input"""

    session_id: str = Field(..., description="Session ID for this request")
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


class MessageDataKind(str, Enum):
    """Types of messages exchanged with agents"""

    TEXT = "text"
    IMAGE = "image"
    COMMAND = "command"


class MessageChunkMetadata(BaseModel):
    session_id: str = Field(..., description="Session ID for this request")
    user_id: str = Field(..., description="User ID who made this request")


class MessageChunk(BaseModel):
    """Chunk of a message, useful for streaming responses"""

    content: str = Field(..., description="Content of the message chunk")
    is_final: bool = Field(
        default=False, description="Indicates if this is the final chunk"
    )
    kind: MessageDataKind = Field(
        ..., description="The type of data contained in the chunk"
    )
    meta: MessageChunkMetadata = Field(
        ..., description="Metadata associated with the message chunk"
    )


class StreamResponse(BaseModel):
    """Response model for streaming agent responses"""

    is_task_complete: bool = Field(
        default=False,
        description="Indicates whether the task associated with this stream response is complete.",
    )
    content: str = Field(
        ...,
        description="The content of the stream response, typically a chunk of data or message.",
    )


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """

    @abstractmethod
    async def stream(
        self, query, session_id, task_id
    ) -> AsyncGenerator[StreamResponse, None]:
        """
        Process user queries and return streaming responses

        Args:
            query: User query content
            session_id: Session ID
            task_id: Task ID

        Yields:
            StreamResponse: Stream response containing content and completion status
        """
        raise NotImplementedError


# Message response type for agent communication
RemoteAgentResponse = tuple[
    Task, Optional[TaskStatusUpdateEvent | TaskArtifactUpdateEvent]
]

NotificationCallbackType = Callable[[Task], None]
