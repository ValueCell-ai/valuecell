from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration"""

    PENDING = "pending"  # Waiting to be processed
    RUNNING = "running"  # Currently executing
    WAITING_INPUT = "waiting_input"  # Waiting for user input
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # Cancelled by user or system


class TaskPattern(str, Enum):
    """Task pattern enumeration"""

    ONCE = "once"  # One-time task
    RECURRING = "recurring"  # Recurring task


class Task(BaseModel):
    """Task data model"""

    task_id: str = Field(..., description="Unique task identifier")
    remote_task_ids: List[str] = Field(
        default_factory=list,
        description="Task identifier determined by the remote agent after submission",
    )
    query: str = Field(..., description="The task to be performed")
    conversation_id: str = Field(
        ..., description="Conversation ID this task belongs to"
    )
    user_id: str = Field(..., description="User ID who initiated this task")
    agent_name: str = Field(..., description="Name of the agent executing this task")
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current task status"
    )
    pattern: TaskPattern = Field(
        default=TaskPattern.ONCE, description="Task execution pattern"
    )

    # Time-related fields
    created_at: datetime = Field(
        default_factory=datetime.now, description="Task creation time"
    )
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update time"
    )

    # Result and error information
    error_message: Optional[str] = Field(
        None, description="Error message if task failed"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}

    def start_task(self) -> None:
        """Start task execution"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        self.updated_at = datetime.now()

    def complete_task(self) -> None:
        """Complete the task"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def fail_task(self, error_message: str) -> None:
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        self.error_message = error_message

    # TODO: cancel agent remote task
    def cancel_task(self) -> None:
        """Cancel the task"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def is_finished(self) -> bool:
        """Check if task is finished"""
        return self.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]

    def is_running(self) -> bool:
        """Check if task is currently running"""
        return self.status == TaskStatus.RUNNING

    def is_waiting_input(self) -> bool:
        """Check if task is waiting for user input"""
        return self.status == TaskStatus.WAITING_INPUT
