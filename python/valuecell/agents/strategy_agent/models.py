from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .constants import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_MAX_LEVERAGE,
    DEFAULT_MAX_POSITIONS,
    DEFAULT_MAX_SYMBOLS,
    DEFAULT_MODEL_PROVIDER,
)


class TradingMode(str, Enum):
    """Trading mode for a strategy used by UI/leaderboard tags."""

    LIVE = "live"
    VIRTUAL = "virtual"


class TradeType(str, Enum):
    """Semantic trade type for positions."""

    LONG = "LONG"
    SHORT = "SHORT"


class TradeSide(str, Enum):
    """Side for executable trade instruction."""

    BUY = "BUY"
    SELL = "SELL"


class ModelConfig(BaseModel):
    """AI model configuration for strategy."""

    provider: str = Field(
        default=DEFAULT_MODEL_PROVIDER,
        description="Model provider (e.g., 'openrouter', 'google', 'openai')",
    )
    model_id: str = Field(
        default=DEFAULT_AGENT_MODEL,
        description="Model identifier (e.g., 'deepseek-ai/deepseek-v3.1', 'gpt-4o')",
    )
    api_key: str = Field(..., description="API key for the model provider")


class ExchangeConfig(BaseModel):
    """Exchange configuration for trading."""

    exchange_id: Optional[str] = Field(
        default=None, description="Exchange identifier (e.g., 'okx', 'binance')"
    )
    trading_mode: TradingMode = Field(
        default=TradingMode.VIRTUAL, description="Trading mode for this strategy"
    )
    api_key: Optional[str] = Field(
        default=None, description="Exchange API key (required for live trading)"
    )
    secret_key: Optional[str] = Field(
        default=None, description="Exchange secret key (required for live trading)"
    )


class TradingConfig(BaseModel):
    """Trading strategy configuration."""

    strategy_name: Optional[str] = Field(
        default=None, description="User-friendly name for this strategy"
    )
    initial_capital: Optional[float] = Field(
        default=DEFAULT_INITIAL_CAPITAL,
        description="Initial capital for trading in USD",
        gt=0,
    )
    max_leverage: float = Field(
        default=DEFAULT_MAX_LEVERAGE,
        description="Maximum leverage",
        gt=0,
    )
    max_positions: int = Field(
        default=DEFAULT_MAX_POSITIONS,
        description="Maximum number of concurrent positions",
        gt=0,
    )
    symbols: List[str] = Field(
        ...,
        description="List of crypto symbols to trade (e.g., ['BTC-USD', 'ETH-USD'])",
    )
    decide_interval: int = Field(
        default=60,
        description="Check interval in seconds",
        gt=0,
    )
    template_id: Optional[str] = Field(
        default=None, description="Strategy template identifier to guide the agent"
    )
    custom_prompt: Optional[str] = Field(
        default=None,
        description="Optional custom prompt to customize strategy behavior",
    )

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one symbol is required")
        if len(v) > DEFAULT_MAX_SYMBOLS:
            raise ValueError(f"Maximum {DEFAULT_MAX_SYMBOLS} symbols allowed")
        # Normalize symbols to uppercase
        return [s.upper() for s in v]


class UserRequest(BaseModel):
    """User-specified strategy request / configuration.

    This model captures the inputs a user (or frontend) sends to create or
    update a strategy instance. It was previously named `Strategy`.
    """

    model_config: ModelConfig = Field(
        default_factory=ModelConfig, description="AI model configuration"
    )
    exchange_config: ExchangeConfig = Field(
        default_factory=ExchangeConfig, description="Exchange configuration for trading"
    )
    trading_config: TradingConfig = Field(
        ..., description="Trading strategy configuration"
    )


# =========================
# Minimal DTOs for Strategy Agent (LLM-driven composer, no StrategyHint)
# These DTOs define the data contract across modules following the
# simplified pipeline: data -> features -> composer(LLM+rules) -> execution -> history/digest.
# =========================


class InstrumentRef(BaseModel):
    """Identifies a tradable instrument.

    - symbol: exchange symbol, e.g., "BTCUSDT"
    - exchange_id: optional exchange id, e.g., "binance", "virtual"
    - quote_ccy: optional quote currency, e.g., "USDT"
    """

    symbol: str = Field(..., description="Exchange symbol, e.g., BTCUSDT")
    exchange_id: Optional[str] = Field(
        default=None, description="exchange identifier (e.g., binance)"
    )
    quote_ccy: Optional[str] = Field(
        default=None, description="Quote currency (e.g., USDT)"
    )


class Candle(BaseModel):
    """Aggregated OHLCV candle for a fixed interval."""

    ts: int = Field(..., description="Candle end timestamp in ms")
    instrument: InstrumentRef
    open: float
    high: float
    low: float
    close: float
    volume: float
    interval: str = Field(..., description='Interval string, e.g., "1m", "5m"')


class FeatureVector(BaseModel):
    """Computed features for a single instrument at a point in time."""

    ts: int
    instrument: InstrumentRef
    values: Dict[str, float] = Field(
        default_factory=dict, description="Feature name to numeric value"
    )
    meta: Optional[Dict[str, float | int | str]] = Field(
        default=None, description="Optional metadata (e.g., window lengths)"
    )


class StrategyStatus(str, Enum):
    """High-level runtime status for strategies (for UI health dot)."""

    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class PositionSnapshot(BaseModel):
    """Current position snapshot for one instrument."""

    instrument: InstrumentRef
    quantity: float = Field(..., description="Position quantity (+long, -short)")
    avg_price: Optional[float] = Field(default=None, description="Average entry price")
    mark_price: Optional[float] = Field(
        default=None, description="Current mark/reference price for P&L calc"
    )
    unrealized_pnl: Optional[float] = Field(default=None, description="Unrealized PnL")
    # Optional fields useful for UI and reporting
    notional: Optional[float] = Field(
        default=None, description="Position notional in quote currency"
    )
    leverage: Optional[float] = Field(
        default=None, description="Leverage applied to the position (if any)"
    )
    entry_ts: Optional[int] = Field(
        default=None, description="Entry timestamp (ms) for the current position"
    )
    pnl_pct: Optional[float] = Field(
        default=None, description="Unrealized P&L as a percent of position value"
    )
    trade_type: Optional[TradeType] = Field(
        default=None, description="Semantic trade type, e.g., 'long' or 'short'"
    )


class PortfolioView(BaseModel):
    """Portfolio state used by the composer for decision making."""

    strategy_id: Optional[str] = Field(
        default=None, description="Owning strategy id for this portfolio snapshot"
    )
    ts: int
    cash: float
    positions: Dict[str, PositionSnapshot] = Field(
        default_factory=dict, description="Map symbol -> PositionSnapshot"
    )
    gross_exposure: Optional[float] = Field(
        default=None, description="Absolute exposure (optional)"
    )
    net_exposure: Optional[float] = Field(
        default=None, description="Net exposure (optional)"
    )
    constraints: Optional[Dict[str, float | int]] = Field(
        default=None,
        description="Optional risk/limits snapshot (e.g., max position, step size)",
    )
    # Optional aggregated fields convenient for UI
    total_value: Optional[float] = Field(
        default=None, description="Total portfolio value (cash + positions)"
    )
    total_unrealized_pnl: Optional[float] = Field(
        default=None, description="Sum of unrealized PnL across positions"
    )
    available_cash: Optional[float] = Field(
        default=None, description="Cash available for new positions"
    )


class LlmDecisionAction(str, Enum):
    """Normalized high-level action from LLM plan item.

    Semantics:
    - BUY/SELL: directional intent; final TradeSide is decided by delta (target - current)
    - FLAT: target position is zero (may produce close-out instructions)
    - NOOP: target equals current (delta == 0), no instruction should be emitted
    """

    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"
    NOOP = "noop"


class LlmDecisionItem(BaseModel):
    """One LLM plan item. Uses target_qty only (no delta).

    The composer will compute order quantity as: target_qty - current_qty.
    """

    instrument: InstrumentRef
    action: LlmDecisionAction
    target_qty: float = Field(
        ..., description="Desired position quantity after execution"
    )
    confidence: Optional[float] = Field(
        default=None, description="Optional confidence score [0,1]"
    )
    rationale: Optional[str] = Field(
        default=None, description="Optional natural language rationale"
    )


class LlmPlanProposal(BaseModel):
    """Structured LLM output before rule normalization."""

    ts: int
    items: List[LlmDecisionItem] = Field(default_factory=list)
    notes: Optional[List[str]] = Field(default=None)
    model_meta: Optional[Dict[str, str]] = Field(
        default=None, description="Optional model metadata (e.g., model_name)"
    )


class TradeInstruction(BaseModel):
    """Executable instruction emitted by the composer after normalization."""

    instruction_id: str = Field(
        ..., description="Deterministic id for idempotency (e.g., compose_id+symbol)"
    )
    compose_id: str = Field(
        ..., description="Decision cycle id to correlate instructions and history"
    )
    instrument: InstrumentRef
    side: TradeSide
    quantity: float = Field(..., description="Order quantity in instrument units")
    price_mode: str = Field(
        ..., description='"market" or "limit" (initial versions may use only "market")'
    )
    limit_price: Optional[float] = Field(default=None)
    max_slippage_bps: Optional[float] = Field(default=None)
    meta: Optional[Dict[str, str | float]] = Field(
        default=None, description="Optional metadata for auditing"
    )


class MetricPoint(BaseModel):
    """Generic time-value point, used for value history charts."""

    ts: int
    value: float


class PortfolioValueSeries(BaseModel):
    """Series for portfolio total value over time (for performance charts)."""

    strategy_id: Optional[str] = Field(default=None)
    points: List[MetricPoint] = Field(default_factory=list)


class ComposeContext(BaseModel):
    """Context assembled for the LLM-driven composer."""

    ts: int
    compose_id: str = Field(
        ..., description="Decision cycle id generated by coordinator per strategy"
    )
    strategy_id: Optional[str] = Field(
        default=None, description="Owning strategy id for logging/aggregation"
    )
    features: List[FeatureVector] = Field(
        default_factory=list, description="Feature vectors across instruments"
    )
    portfolio: PortfolioView
    digest: "TradeDigest"
    prompt_text: str = Field(..., description="Strategy/style prompt text")
    market_snapshot: Optional[Dict[str, float]] = Field(
        default=None, description="Optional map symbol -> current reference price"
    )
    constraints: Optional[Dict[str, float | int]] = Field(
        default=None, description="Optional extra constraints for guardrails"
    )


class HistoryRecord(BaseModel):
    """Generic persisted record for post-hoc analysis and digest building."""

    ts: int
    kind: str = Field(
        ..., description='"features" | "compose" | "instructions" | "execution"'
    )
    reference_id: str = Field(..., description="Correlation id (e.g., compose_id)")
    payload: Dict[str, object] = Field(default_factory=dict)


class TradeDigestEntry(BaseModel):
    """Digest stats per instrument for historical guidance in composer."""

    instrument: InstrumentRef
    trade_count: int
    realized_pnl: float
    win_rate: Optional[float] = Field(default=None)
    avg_holding_ms: Optional[int] = Field(default=None)
    last_trade_ts: Optional[int] = Field(default=None)
    avg_entry_price: Optional[float] = Field(default=None)
    max_drawdown: Optional[float] = Field(default=None)
    recent_performance_score: Optional[float] = Field(default=None)


class TradeHistoryEntry(BaseModel):
    """Executed trade record for UI history and auditing.

    This model is intended to be a compact, display-friendly representation
    of a completed trade (entry + exit). Fields are optional to allow
    use for partially filled / in-progress records.
    """

    trade_id: Optional[str] = Field(default=None, description="Unique trade id")
    compose_id: Optional[str] = Field(
        default=None, description="Originating decision cycle id (if applicable)"
    )
    instruction_id: Optional[str] = Field(
        default=None, description="Instruction id that initiated this trade"
    )
    strategy_id: Optional[str] = Field(default=None)
    instrument: InstrumentRef
    side: TradeSide
    type: TradeType
    quantity: float
    entry_price: Optional[float] = Field(default=None)
    exit_price: Optional[float] = Field(default=None)
    notional_entry: Optional[float] = Field(default=None)
    notional_exit: Optional[float] = Field(default=None)
    entry_ts: Optional[int] = Field(default=None, description="Entry timestamp ms")
    exit_ts: Optional[int] = Field(default=None, description="Exit timestamp ms")
    trade_ts: Optional[int] = Field(default=None, description="Trade timestamp in ms")
    holding_ms: Optional[int] = Field(default=None, description="Holding time in ms")
    realized_pnl: Optional[float] = Field(default=None)
    realized_pnl_pct: Optional[float] = Field(default=None)
    leverage: Optional[float] = Field(default=None)
    note: Optional[str] = Field(
        default=None, description="Optional free-form note or comment about the trade"
    )


class TradeDigest(BaseModel):
    """Compact digest used by the composer as historical reference."""

    ts: int
    by_instrument: Dict[str, TradeDigestEntry] = Field(default_factory=dict)


class StrategySummary(BaseModel):
    """Minimal summary for leaderboard and quick status views.

    Purely for UI aggregation; does not affect the compose pipeline.
    All fields are optional to avoid breaking callers and allow
    progressive enhancement by the backend.
    """

    strategy_id: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    model_provider: Optional[str] = Field(default=None)
    model_id: Optional[str] = Field(default=None)
    exchange_id: Optional[str] = Field(default=None)
    mode: Optional[TradingMode] = Field(default=None)
    status: Optional[StrategyStatus] = Field(default=None)
    realized_pnl: Optional[float] = Field(
        default=None, description="Realized P&L in quote CCY"
    )
    unrealized_pnl: Optional[float] = Field(
        default=None, description="Unrealized P&L in quote CCY"
    )
    pnl_pct: Optional[float] = Field(
        default=None, description="P&L as percent of equity or initial capital"
    )
    last_updated_ts: Optional[int] = Field(default=None)
