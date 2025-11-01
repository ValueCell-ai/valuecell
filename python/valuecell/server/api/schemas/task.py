"""Task API schemas."""

from typing import List

from pydantic import BaseModel, Field

from .base import SuccessResponse


class TaskCancelData(BaseModel):
    """Data returned after attempting to cancel a task."""

    task_id: str = Field(..., description="The task ID that was processed")
    success: bool = Field(
        ..., description="Whether the task was successfully cancelled"
    )
    updated_component_ids: List[str] = Field(
        default_factory=list,
        description="IDs of scheduled_task_controller components updated to 'cancelled'",
    )


# Response type for task cancel
TaskCancelResponse = SuccessResponse[TaskCancelData]
