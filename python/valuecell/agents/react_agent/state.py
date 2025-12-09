from __future__ import annotations

from operator import ior
from typing import Any, Annotated, TypedDict


class AgentState(TypedDict, total=False):
    # Conversation and intent
    messages: list[Any]
    user_profile: dict[str, Any] | None
    inquirer_turns: int

    # Planning
    plan: list[dict[str, Any]] | None
    plan_logic: str | None

    # Execution results (merged across parallel executors)
    completed_tasks: Annotated[dict[str, Any], ior]
    
    # Track dispatched tasks to prevent duplicate scheduling (merged across routing passes)
    _dispatched: Annotated[dict[str, bool], ior]

    # Scheduler internal fields
    _schedule_status: str | None
    _runnable: list[dict[str, Any]] | None

    # Critic decision
    next_action: Any | None
    _critic_summary: Any | None

    # Misc
    missing_info_field: str | None
    user_supplement_info: Any | None
