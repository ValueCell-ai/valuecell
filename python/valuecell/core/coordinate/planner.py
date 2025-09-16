from datetime import datetime
from typing import List

from valuecell.utils import generate_uuid
from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.task import Task, TaskStatus
from valuecell.core.types import UserInput

from .models import ExecutionPlan


class ExecutionPlanner:
    """Simple execution planner that analyzes user input and creates execution plans"""

    def __init__(self, agent_connections: RemoteConnections):
        self.agent_connections = agent_connections

    async def create_plan(self, user_input: UserInput) -> ExecutionPlan:
        """Create an execution plan from user input"""

        plan = ExecutionPlan(
            plan_id=generate_uuid("plan"),
            session_id=user_input.meta.session_id,
            user_id=user_input.meta.user_id,
            query=user_input.query,
            created_at=datetime.now().isoformat(),
        )

        # Simple planning logic - create tasks directly with user_id context
        tasks = await self._analyze_input_and_create_tasks(user_input)
        plan.tasks = tasks

        return plan

    async def _analyze_input_and_create_tasks(
        self, user_input: UserInput
    ) -> List[Task]:
        """Analyze user input and create tasks for appropriate agents"""

        # Check if user specified a desired agent
        if user_input.has_desired_agent():
            desired_agent = user_input.get_desired_agent()
            available_agents = self.agent_connections.list_available_agents()

            # If the desired agent exists, use it directly
            if desired_agent in available_agents:
                return [
                    self._create_task(
                        user_input.meta.session_id,
                        user_input.meta.user_id,
                        desired_agent,
                    )
                ]

        raise ValueError("No suitable agent found for the request.")

    def _create_task(self, session_id: str, user_id: str, agent_name: str) -> Task:
        """Create a new task for the specified agent"""
        return Task(
            task_id=generate_uuid("task"),
            session_id=session_id,
            user_id=user_id,
            agent_name=agent_name,
            status=TaskStatus.PENDING,
        )

    async def add_task(self, plan: ExecutionPlan, agent_name: str) -> None:
        """Add a task to an existing plan"""
        task = self._create_task(plan.session_id, plan.user_id, agent_name)
        plan.tasks.append(task)
