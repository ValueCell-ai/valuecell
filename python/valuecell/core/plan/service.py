"""Planning service coordinating planner and user input lifecycle."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Dict, Optional

from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.plan.planner import (
    ExecutionPlanner,
    UserInputRequest,
)
from valuecell.core.types import UserInput


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

        return asyncio.create_task(
            self._planner.create_plan(user_input, callback, thread_id)
        )
