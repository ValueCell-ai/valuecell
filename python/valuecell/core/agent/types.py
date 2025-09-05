from abc import ABC, abstractmethod
from typing import Optional

from a2a.types import Task, TaskArtifactUpdateEvent, TaskStatusUpdateEvent
from pydantic import BaseModel, Field


class StreamResponse(BaseModel):
    is_task_complete: bool = Field(
        default=False,
        description="Indicates whether the task associated with this stream response is complete.",
    )
    content: str = Field(
        ...,
        description="The content of the stream response, typically a chunk of data or message.",
    )


class BaseAgent(ABC, BaseModel):
    """
    Abstract base class for all agents.
    """

    agent_name: str = Field(..., description="Unique name of the agent")
    description: str = Field(
        ..., description="Description of the agent's purpose and functionality"
    )

    @abstractmethod
    async def stream(self, query, session_id, task_id) -> StreamResponse:
        """
        Abstract method to stream the agent with the provided input data.
        Must be implemented by all subclasses.
        """


MessageResponse = tuple[Task, Optional[TaskStatusUpdateEvent | TaskArtifactUpdateEvent]]
