"""
Strategy API schemas for handling strategy-related requests and responses.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .base import SuccessResponse


class StrategySummaryData(BaseModel):
    """Summary data for a single strategy per product spec."""

    strategy_id: str = Field(
        ..., description="Runtime strategy identifier from StrategyAgent"
    )
    strategy_name: Optional[str] = Field(None, description="User-defined strategy name")
    status: Literal["running", "stopped"] = Field(..., description="Strategy status")
    trading_mode: Optional[Literal["live", "virtual"]] = Field(
        None, description="Trading mode: live or virtual"
    )
    unrealized_pnl: Optional[float] = Field(None, description="Unrealized PnL value")
    unrealized_pnl_pct: Optional[float] = Field(
        None, description="Unrealized PnL percentage"
    )
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
    available_cash: Optional[float] = Field(
        None, description="Cash available for new positions"
    )


StrategyHoldingResponse = SuccessResponse[StrategyHoldingData]


class StrategyDetailItem(BaseModel):
    trade_id: str = Field(..., description="Unique trade identifier")
    symbol: str = Field(..., description="Instrument symbol")
    type: Literal["LONG", "SHORT"] = Field(..., description="Trade type")
    side: Literal["BUY", "SELL"] = Field(..., description="Entry side")
    leverage: Optional[float] = Field(None, description="Leverage applied")
    quantity: float = Field(..., description="Trade quantity")
    unrealized_pnl: Optional[float] = Field(None, description="Unrealized PnL value")
    entry_price: Optional[float] = Field(None, description="Entry price")
    exit_price: Optional[float] = Field(None, description="Exit price if closed")
    holding_ms: Optional[int] = Field(
        None, description="Holding duration in milliseconds"
    )
    time: Optional[str] = Field(None, description="Entry time in UTC ISO8601")
    note: Optional[str] = Field(None, description="Additional note")


StrategyDetailResponse = SuccessResponse[List[StrategyDetailItem]]


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
