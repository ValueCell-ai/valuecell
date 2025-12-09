from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    id: str
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


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


class InquirerDecision(BaseModel):
    """The decision output from the LLM-driven Inquirer Agent."""

    intent: FinancialIntent = Field(
        description="Extracted financial intent from conversation"
    )
    status: Literal["COMPLETE", "INCOMPLETE"] = Field(
        description="Set to COMPLETE if essential info (risk) is present OR if max turns reached."
    )
    reasoning: str = Field(description="Brief thought process explaining the decision")
    response_to_user: str = Field(
        description="If INCOMPLETE: A follow-up question. If COMPLETE: A confirmation message."
    )
