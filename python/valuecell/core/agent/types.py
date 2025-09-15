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


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """

    @abstractmethod
    async def stream(self, query, session_id, task_id) -> StreamResponse:
        """
        Process user queries and return streaming responses

        Args:
            query: User query content
            session_id: Session ID
            task_id: Task ID

        Yields:
            dict: Dictionary containing 'content' and 'is_task_complete'
        """


MessageResponse = tuple[Task, Optional[TaskStatusUpdateEvent | TaskArtifactUpdateEvent]]
