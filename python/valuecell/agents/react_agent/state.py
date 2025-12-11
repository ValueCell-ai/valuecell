from __future__ import annotations

import operator
from operator import ior
from typing import Annotated, Any, List, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    # Conversation and intent
    messages: Annotated[List[BaseMessage], operator.add]
    current_intent: str | None  # Natural language description of user's immediate goal
    inquirer_turns: int

    # Planning (iterative batch planning)
    plan: list[dict[str, Any]] | None  # Current batch of tasks
    strategy_update: str | None  # Latest planner reasoning summary

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
