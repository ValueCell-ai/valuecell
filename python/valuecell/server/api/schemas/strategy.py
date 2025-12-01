"""
Strategy API schemas for handling strategy-related requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .base import SuccessResponse


class StrategyType(str, Enum):
    PROMPT = "PromptBasedStrategy"
    GRID = "GridStrategy"


class StrategySummaryData(BaseModel):
    """Summary data for a single strategy per product spec."""

    strategy_id: str = Field(
        ..., description="Runtime strategy identifier from StrategyAgent"
    )
    strategy_name: Optional[str] = Field(None, description="User-defined strategy name")
    strategy_type: Optional[StrategyType] = Field(
        None,
        description="Strategy type identifier: 'prompt based strategy' or 'grid strategy'",
    )
    status: Literal["running", "stopped"] = Field(..., description="Strategy status")
    stop_reason: Optional[str] = Field(None, description="Reason for strategy stop")
    trading_mode: Optional[Literal["live", "virtual"]] = Field(
        None, description="Trading mode: live or virtual"
    )
    total_pnl: Optional[float] = Field(None, description="Total PnL value")
    total_pnl_pct: Optional[float] = Field(None, description="Total PnL percentage")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    exchange_id: Optional[str] = Field(
        None, description="Associated exchange identifier"
    )
    model_id: Optional[str] = Field(None, description="Associated model identifier")


class StrategyListData(BaseModel):
    """Data model for strategy list."""

    strategies: List[StrategySummaryData] = Field(..., description="List of strategies")
    total: int = Field(..., description="Total number of strategies")
    running_count: int = Field(..., description="Number of running strategies")


StrategyListResponse = SuccessResponse[StrategyListData]


class PositionHoldingItem(BaseModel):
    symbol: str = Field(..., description="Instrument symbol")
    exchange_id: Optional[str] = Field(None, description="Exchange identifier")
    quantity: float = Field(..., description="Position quantity (+long, -short)")
    avg_price: Optional[float] = Field(None, description="Average entry price")
    mark_price: Optional[float] = Field(
        None, description="Current mark/reference price"
    )
    unrealized_pnl: Optional[float] = Field(None, description="Unrealized PnL value")
    unrealized_pnl_pct: Optional[float] = Field(
        None, description="Unrealized PnL percentage"
    )
    notional: Optional[float] = Field(
        None, description="Position notional in quote currency"
    )
    leverage: Optional[float] = Field(
        None, description="Leverage applied to the position"
    )
    entry_ts: Optional[int] = Field(None, description="Entry timestamp (ms)")
    trade_type: Optional[str] = Field(None, description="Trade type (LONG/SHORT)")


class StrategyHoldingData(BaseModel):
    strategy_id: str = Field(..., description="Strategy identifier")
    ts: int = Field(..., description="Snapshot timestamp in ms")
    cash: float = Field(..., description="Cash balance")
    positions: List[PositionHoldingItem] = Field(
        default_factory=list, description="List of position holdings"
    )
    total_value: Optional[float] = Field(
        None, description="Total portfolio value (cash + positions)"
    )
    total_unrealized_pnl: Optional[float] = Field(
        None, description="Sum of unrealized PnL across positions"
    )
    total_realized_pnl: Optional[float] = Field(
        None, description="Sum of realized PnL from closed positions"
    )
    gross_exposure: Optional[float] = Field(
        None, description="Aggregate gross exposure at snapshot"
    )
    net_exposure: Optional[float] = Field(
        None, description="Aggregate net exposure at snapshot"
    )
    available_cash: Optional[float] = Field(
        None, description="Cash available for new positions"
    )


StrategyHoldingResponse = SuccessResponse[StrategyHoldingData]


class StrategyPortfolioSummaryData(BaseModel):
    strategy_id: str = Field(..., description="Strategy identifier")
    ts: int = Field(..., description="Snapshot timestamp in ms")
    cash: Optional[float] = Field(None, description="Cash balance from snapshot")
    total_value: Optional[float] = Field(
        None, description="Total portfolio value (cash + positions)"
    )
    total_pnl: Optional[float] = Field(
        None,
        description="Combined realized and unrealized PnL for the snapshot",
    )
    total_pnl_pct: Optional[float] = Field(
        None, description="Total PnL percentage for the snapshot"
    )
    gross_exposure: Optional[float] = Field(
        None, description="Aggregate gross exposure at snapshot"
    )
    net_exposure: Optional[float] = Field(
        None, description="Aggregate net exposure at snapshot"
    )


StrategyPortfolioSummaryResponse = SuccessResponse[StrategyPortfolioSummaryData]


class StrategyActionCard(BaseModel):
    instruction_id: str = Field(..., description="Instruction identifier (NOT NULL)")
    symbol: str = Field(..., description="Instrument symbol")
    action: Optional[
        Literal["open_long", "open_short", "close_long", "close_short", "noop"]
    ] = Field(None, description="LLM action (includes noop)")
    action_display: Optional[str] = Field(
        None, description="Human-friendly action label for display, e.g. 'OPEN LONG'"
    )
    side: Optional[Literal["BUY", "SELL"]] = Field(
        None, description="Derived execution side"
    )
    quantity: Optional[float] = Field(None, description="Order quantity (units)")
    leverage: Optional[float] = Field(
        None, description="Leverage applied to the instruction (if any)"
    )
    avg_exec_price: Optional[float] = Field(
        None, description="Average execution price for fills"
    )
    entry_price: Optional[float] = Field(None, description="Entry price")
    exit_price: Optional[float] = Field(None, description="Exit price (if closed)")
    entry_at: Optional[datetime] = Field(None, description="Entry timestamp")
    exit_at: Optional[datetime] = Field(None, description="Exit timestamp")
    holding_time_ms: Optional[int] = Field(
        None, description="Holding time in milliseconds"
    )
    notional_entry: Optional[float] = Field(
        None, description="Entry notional in quote currency"
    )
    notional_exit: Optional[float] = Field(
        None, description="Exit notional in quote currency"
    )
    fee_cost: Optional[float] = Field(
        None, description="Total fees charged in quote currency"
    )
    realized_pnl: Optional[float] = Field(None, description="Realized PnL on close")
    realized_pnl_pct: Optional[float] = Field(
        None, description="Realized PnL percentage on close"
    )
    rationale: Optional[str] = Field(None, description="LLM rationale text")


class StrategyCycleDetail(BaseModel):
    compose_id: str = Field(..., description="Compose cycle identifier")
    cycle_index: int = Field(..., description="Cycle index (1-based)")
    created_at: datetime = Field(..., description="Compose datetime")
    rationale: Optional[str] = Field(None, description="LLM rationale text")
    actions: List[StrategyActionCard] = Field(
        default_factory=list, description="Instruction/action cards for this cycle"
    )


StrategyDetailResponse = SuccessResponse[List[StrategyCycleDetail]]


class StrategyHoldingFlatItem(BaseModel):
    symbol: str = Field(..., description="Instrument symbol")
    type: Literal["LONG", "SHORT"] = Field(
        ..., description="Trade type derived from position"
    )
    leverage: Optional[float] = Field(None, description="Leverage applied")
    entry_price: Optional[float] = Field(None, description="Average entry price")
    quantity: float = Field(..., description="Absolute position quantity")
    unrealized_pnl: Optional[float] = Field(None, description="Unrealized PnL value")
    unrealized_pnl_pct: Optional[float] = Field(
        None, description="Unrealized PnL percentage"
    )


# Response type for compact holdings array
StrategyHoldingFlatResponse = SuccessResponse[List[StrategyHoldingFlatItem]]


StrategyCurveResponse = SuccessResponse[List[List[str | float | None]]]


class StrategyStatusUpdateResponse(BaseModel):
    strategy_id: str = Field(..., description="Strategy identifier")
    status: Literal["running", "stopped"] = Field(
        ..., description="Updated strategy status"
    )
    message: str = Field(..., description="Status update message")


StrategyStatusSuccessResponse = SuccessResponse[StrategyStatusUpdateResponse]


# =====================
# Prompt Schemas (strategy namespace)
# =====================


class PromptItem(BaseModel):
    id: str = Field(..., description="Prompt UUID")
    name: str = Field(..., description="Prompt name")
    content: str = Field(..., description="Prompt content text")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")


class PromptCreateRequest(BaseModel):
    name: str = Field(..., description="Prompt name")
    content: str = Field(..., description="Prompt content text")


PromptListResponse = SuccessResponse[list[PromptItem]]
PromptCreateResponse = SuccessResponse[PromptItem]


class StrategyPerformanceData(BaseModel):
    """Performance overview for a strategy including ROI and config."""

    strategy_id: str = Field(..., description="Strategy identifier")
    initial_capital: Optional[float] = Field(
        None, description="Initial capital used by the strategy"
    )
    return_rate_pct: Optional[float] = Field(
        None, description="Return rate percentage relative to initial capital"
    )
    # Flattened config fields (only the requested subset)
    llm_provider: Optional[str] = Field(
        None, description="Model provider (e.g., openrouter, google, openai)"
    )
    llm_model_id: Optional[str] = Field(
        None, description="Model identifier (e.g., deepseek-ai/deepseek-v3.1)"
    )
    exchange_id: Optional[str] = Field(None, description="Exchange identifier")
    strategy_type: Optional[StrategyType] = Field(
        None, description="Strategy type (PromptBasedStrategy/GridStrategy)"
    )
    max_leverage: Optional[float] = Field(None, description="Maximum leverage")
    symbols: Optional[List[str]] = Field(None, description="Symbols universe")
    prompt: Optional[str] = Field(
        None, description="Final resolved prompt text used by the strategy"
    )


StrategyPerformanceResponse = SuccessResponse[StrategyPerformanceData]
