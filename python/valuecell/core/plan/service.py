"""Planning service coordinating planner and user input lifecycle.

Enhancement: supports "planner passthrough" agents. When a target agent is
marked as passthrough (flag captured by RemoteConnections at startup), the
planner will skip running the LLM planning agent and directly synthesize a
single-task ExecutionPlan that hands the user's query to the specified agent.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Awaitable, Callable, Dict, Optional

from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.plan.models import ExecutionPlan
from valuecell.core.plan.planner import (
    ExecutionPlanner,
    UserInputRequest,
)
from valuecell.core.task.models import Task
from valuecell.core.types import UserInput
from valuecell.utils import generate_uuid


class UserInputRegistry:
    """In-memory store for pending planner-driven user input requests."""

    def __init__(self) -> None:
        self._pending: Dict[str, UserInputRequest] = {}

    def add_request(self, conversation_id: str, request: UserInputRequest) -> None:
        self._pending[conversation_id] = request

    def has_request(self, conversation_id: str) -> bool:
        return conversation_id in self._pending

    def get_prompt(self, conversation_id: str) -> Optional[str]:
        request = self._pending.get(conversation_id)
        return request.prompt if request else None

    def provide_response(self, conversation_id: str, response: str) -> bool:
        if conversation_id not in self._pending:
            return False
        request = self._pending.pop(conversation_id)
        request.provide_response(response)
        return True

    def clear(self, conversation_id: str) -> None:
        self._pending.pop(conversation_id, None)


class PlanService:
    """Encapsulate plan creation and Human-in-the-Loop state."""

    def __init__(
        self,
        agent_connections: RemoteConnections,
        execution_planner: ExecutionPlanner | None = None,
        user_input_registry: UserInputRegistry | None = None,
    ) -> None:
        self._agent_connections = agent_connections
        self._planner = execution_planner or ExecutionPlanner(agent_connections)
        self._input_registry = user_input_registry or UserInputRegistry()

    @property
    def planner(self) -> ExecutionPlanner:
        return self._planner

    def register_user_input(
        self, conversation_id: str, request: UserInputRequest
    ) -> None:
        self._input_registry.add_request(conversation_id, request)

    def has_pending_request(self, conversation_id: str) -> bool:
        return self._input_registry.has_request(conversation_id)

    def get_request_prompt(self, conversation_id: str) -> Optional[str]:
        return self._input_registry.get_prompt(conversation_id)

    def provide_user_response(self, conversation_id: str, response: str) -> bool:
        return self._input_registry.provide_response(conversation_id, response)

    def clear_pending_request(self, conversation_id: str) -> None:
        self._input_registry.clear(conversation_id)

    def start_planning_task(
        self,
        user_input: UserInput,
        thread_id: str,
        callback: Callable[[UserInputRequest], Awaitable[None]],
    ) -> asyncio.Task:
        """Kick off asynchronous planning."""

        agent_name = (user_input.target_agent_name or "").strip()
        is_passthrough = False
        if agent_name:
            try:
                is_passthrough = bool(
                    self._agent_connections.is_planner_passthrough(agent_name)
                )
            except Exception:
                is_passthrough = False
            if is_passthrough:
                # Directly create a simple one-task plan without invoking the LLM planner
                return asyncio.create_task(
                    self._create_passthrough_plan(user_input, thread_id)
                )

        return asyncio.create_task(
            self._planner.create_plan(user_input, callback, thread_id)
        )

    # ------------------------
    # Internal helpers
    # ------------------------
    async def _create_passthrough_plan(
        self, user_input: UserInput, thread_id: str
    ) -> ExecutionPlan:
        """Synthesize a simple one-task plan that directly invokes target agent.

        The produced plan mirrors the structure of a normal planner output but
        avoids any LLM calls. It simply wraps the user's query into a Task
        addressed to the target agent.
        """
        conversation_id = user_input.meta.conversation_id
        plan = ExecutionPlan(
            plan_id=generate_uuid("plan"),
            conversation_id=conversation_id,
            user_id=user_input.meta.user_id,
            orig_query=user_input.query,
            created_at=datetime.now().isoformat(),
        )

        agent_name = user_input.target_agent_name or ""
        # Keep a concise title so UI/conversation title can reuse it
        title = f"Run {agent_name}".strip()
        task = Task(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_id=user_input.meta.user_id,
            agent_name=agent_name,
            title=title,
            query=user_input.query,
        )
        plan.tasks = [task]
        return plan
