from __future__ import annotations

from operator import ior
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    # Conversation and intent
    messages: list[Any]
    user_profile: dict[str, Any] | None
    inquirer_turns: int

    # Planning (iterative batch planning)
    plan: list[dict[str, Any]] | None  # Current batch of tasks
    plan_logic: str | None  # Deprecated: replaced by strategy_update

    # Execution results (merged across parallel executors)
    completed_tasks: Annotated[dict[str, Any], ior]

    # Iterative planning: growing list of execution summaries
    execution_history: Annotated[list[str], list.__add__]

    # Feedback from Critic to guide next planning iteration
    critique_feedback: str | None

    # Flag to signal Planner believes goal is complete
    is_final: bool

    # Critic decision
    next_action: Any | None
    _critic_summary: Any | None

    # Misc
    missing_info_field: str | None
    user_supplement_info: Any | None
