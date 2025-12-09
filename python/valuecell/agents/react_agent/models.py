from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str
    tool_name: Literal["market_data", "screen", "backtest", "summary"]
    tool_args: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class FinancialIntent(BaseModel):
    asset_symbols: Optional[list[str]] = None
    risk: Optional[Literal["Low", "Medium", "High"]] = None


class ExecutorResult(BaseModel):
    task_id: str
    ok: bool = True
    result: Any | None = None
    error: Optional[str] = None
    error_code: Optional[str] = None  # e.g., ERR_NETWORK, ERR_INPUT


class InquirerDecision(BaseModel):
    """The decision output from the LLM-driven Inquirer Agent."""
    intent: FinancialIntent = Field(description="Extracted financial intent from conversation")
    status: Literal["COMPLETE", "INCOMPLETE"] = Field(
        description="Set to COMPLETE if essential info (risk) is present OR if max turns reached."
    )
    reasoning: str = Field(description="Brief thought process explaining the decision")
    response_to_user: str = Field(
        description="If INCOMPLETE: A follow-up question. If COMPLETE: A confirmation message."
    )
