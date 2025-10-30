from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from valuecell.utils.uuid import generate_task_id, generate_thread_id


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


class ScheduleConfig(BaseModel):
    """Schedule configuration for recurring tasks"""

    interval_minutes: Optional[int] = Field(
        None,
        description="Interval in minutes for recurring execution (e.g., 60 for every hour)",
    )
    daily_time: Optional[str] = Field(
        None,
        description="Daily execution time in HH:MM format (e.g., '09:00' for 9 AM)",
    )

    def is_valid(self) -> bool:
        """Check if the schedule configuration is valid"""
        return self.interval_minutes is not None or self.daily_time is not None


class Task(BaseModel):
    """Task data model"""

    task_id: str = Field(
        default_factory=generate_task_id, description="Unique task identifier"
    )
    remote_task_ids: List[str] = Field(
        default_factory=list,
        description="Task identifier determined by the remote agent after submission",
    )
    title: str = Field(
        default="",
        description="A concise task title or summary (<=10 words or characters)",
    )
    query: str = Field(..., description="The task to be performed")
    conversation_id: str = Field(
        ..., description="Conversation ID this task belongs to"
    )
    thread_id: str = Field(
        default_factory=generate_thread_id, description="Thread ID this task belongs to"
    )
    user_id: str = Field(..., description="User ID who initiated this task")
    agent_name: str = Field(..., description="Name of the agent executing this task")
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current task status"
    )
    pattern: TaskPattern = Field(
        default=TaskPattern.ONCE, description="Task execution pattern"
    )
    schedule_config: Optional[ScheduleConfig] = Field(
        None, description="Schedule configuration for recurring tasks"
    )
    handoff_from_super_agent: bool = Field(
        False,
        description="Indicates if the task was handed over from a super agent",
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

    def start(self) -> None:
        """Start task execution"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        self.updated_at = datetime.now()

    def complete(self) -> None:
        """Complete the task"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def fail(self, error_message: str) -> None:
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        self.error_message = error_message

    # TODO: cancel agent remote task
    def cancel(self) -> None:
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

    def is_scheduled(self) -> bool:
        """Check if task is scheduled for recurring execution"""
        return (
            self.pattern == TaskPattern.RECURRING
            and self.schedule_config is not None
            and self.schedule_config.is_valid()
        )
