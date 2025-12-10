from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    id: str
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)


class FinancialIntent(BaseModel):
    asset_symbols: Optional[list[str]] = None
    risk: Optional[Literal["Low", "Medium", "High"]] = None

    @field_validator("asset_symbols", mode="before")
    def _coerce_asset_symbols(cls, v):
        """Allow a single string symbol to be provided and coerce to list[str].

        Examples:
        - "AAPL" -> ["AAPL"]
        - ["AAPL", "MSFT"] -> ["AAPL", "MSFT"]
        - None -> None
        """
        if v is None:
            return None
        # If a single string provided, wrap it
        if isinstance(v, str):
            return [v]
        # If tuple, convert to list
        if isinstance(v, tuple):
            return list(v)
        # Otherwise assume it's already an iterable/list-like
        return v


class ExecutorResult(BaseModel):
    task_id: str
    ok: bool = True
    result: Any | None = None
    error: Optional[str] = None
    error_code: Optional[str] = None  # e.g., ERR_NETWORK, ERR_INPUT


ARG_VAL_TYPES = str | int | float | bool


class PlannedTask(BaseModel):
    id: str = Field(description="Unique task identifier, e.g., 't1'")
    tool_id: str = Field(description="The EXACT tool_id from the available tool list")
    tool_args: Dict[str, ARG_VAL_TYPES | list[ARG_VAL_TYPES]] = Field(
        default_factory=dict,
        description="The arguments to pass to the tool. "
        "MUST strictly match the 'Arguments' list in the tool definition. "
        "DO NOT leave empty if the tool requires parameters. "
        "Example: {'symbol': 'AAPL', 'period': '1y'}",
    )
    description: str = Field(description="Short description for logs")


class ExecutionPlan(BaseModel):
    """Output from the Planner for iterative batch planning."""

    tasks: list[PlannedTask] = Field(
        description="List of tasks to execute concurrently in this batch."
    )
    strategy_update: str = Field(
        description="Brief reasoning about what has been done and what is left."
    )
    is_final: bool = Field(
        default=False,
        description="Set to True ONLY if the user's goal is fully satisfied.",
    )


class InquirerDecision(BaseModel):
    """The decision output from the LLM-driven Inquirer Agent with context-switching."""

    intent: FinancialIntent | None = Field(
        default=None, description="Extracted financial intent from conversation"
    )
    status: Literal["COMPLETE", "INCOMPLETE", "CHAT"] = Field(
        description="COMPLETE: Ready for planning. INCOMPLETE: Need more info. CHAT: Casual conversation/follow-up."
    )
    reasoning: str = Field(description="Brief thought process explaining the decision")
    response_to_user: str | None = Field(
        default=None,
        description="Direct response to user (for INCOMPLETE questions or CHAT replies).",
    )
    should_clear_history: bool = Field(
        default=False,
        description="True if user is starting a NEW task (e.g., changing stocks). "
        "False if asking follow-up questions about existing analysis.",
    )
