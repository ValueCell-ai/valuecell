from typing import List
from pydantic import BaseModel, Field

from valuecell.core.task import Task


class ExecutionPlan(BaseModel):
    """Execution plan containing multiple tasks"""

    plan_id: str = Field(..., description="Unique plan identifier")
    session_id: str = Field(..., description="Session ID this plan belongs to")
    user_id: str = Field(..., description="User ID who requested this plan")
    query: str = Field(..., description="Original user input")
    tasks: List[Task] = Field(default_factory=list, description="Tasks to execute")
    created_at: str = Field(..., description="Plan creation timestamp")
