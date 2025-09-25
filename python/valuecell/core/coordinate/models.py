from typing import List, Optional

from pydantic import BaseModel, Field
from valuecell.core.task import Task
from valuecell.core.task.models import TaskPattern


class ExecutionPlan(BaseModel):
    """
    Execution plan containing multiple tasks for fulfilling a user request.

    This model represents a structured plan that breaks down a user's request
    into executable tasks that can be processed by different agents.
    """

    plan_id: str = Field(..., description="Unique plan identifier")
    conversation_id: Optional[str] = Field(
        ..., description="Conversation ID this plan belongs to"
    )
    user_id: str = Field(..., description="User ID who requested this plan")
    orig_query: str = Field(
        ..., description="Original user query that generated this plan"
    )
    tasks: List[Task] = Field(default_factory=list, description="Tasks to execute")
    created_at: str = Field(..., description="Plan creation timestamp")


class _TaskBrief(BaseModel):
    """
    Represents a task to be executed by an agent.

    This is a simplified task representation used during the planning phase
    before being converted to a full Task object.
    """

    query: str = Field(..., description="The task to be performed")
    agent_name: str = Field(..., description="Name of the agent executing this task")
    pattern: TaskPattern = Field(
        default=TaskPattern.ONCE, description="Task execution pattern"
    )


class PlannerInput(BaseModel):
    """
    Schema for planner input containing user query and metadata.

    This schema is used by the planning agent to structure its input
    when determining what tasks should be executed.
    """

    desired_agent_name: str = Field(
        ..., description="The name of the agent the user wants to use for the task"
    )
    query: str = Field(
        ..., description="The user's input or request which may need clarification"
    )


class PlannerResponse(BaseModel):
    """
    Schema for planner response containing tasks and planning metadata.

    This schema is used by the planning agent to structure its response
    when determining what tasks should be executed.
    """

    tasks: List[_TaskBrief] = Field(..., description="List of tasks to be executed")
    adequate: bool = Field(
        ...,
        description="true if information is adequate for task execution, false if more input is needed",
    )
    reason: str = Field(..., description="Reason for the planning decision")
