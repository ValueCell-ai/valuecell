from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .constants import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_CAP_FACTOR,
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


class ComponentType(str, Enum):
    """Component types for StrategyAgent streaming responses."""

    STATUS = "strategy_agent_status"
    UPDATE_TRADE = "strategy_agent_update_trade"
    UPDATE_PORTFOLIO = "strategy_agent_update_portfolio"
    UPDATE_STRATEGY_SUMMARY = "strategy_agent_update_strategy_summary"


class LLMModelConfig(BaseModel):
    """AI model configuration for strategy.

    Defaults are harmonized with backend ConfigManager so that
    Strategy creation uses the same provider/model as GET /models/llm/config.
    """

    provider: str = Field(
        default=DEFAULT_MODEL_PROVIDER,
        description="Model provider (e.g., 'openrouter', 'google', 'openai')",
    )
    model_id: str = Field(
        default=DEFAULT_AGENT_MODEL,
        description="Model identifier (e.g., 'deepseek-ai/deepseek-v3.1', 'gpt-4o')",
    )
    api_key: str = Field(..., description="API key for the model provider")

    @model_validator(mode="before")
    @classmethod
    def _fill_defaults(cls, data):
        # Allow requests to omit provider/model/api_key and backfill from ConfigManager
        if not isinstance(data, dict):
            return data
        values = dict(data)
        try:
            from valuecell.config.manager import get_config_manager

            manager = get_config_manager()
            resolved_provider = (
                values.get("provider")
                or getattr(manager, "primary_provider", None)
                or DEFAULT_MODEL_PROVIDER
            )
            provider_cfg = manager.get_provider_config(resolved_provider)
            if provider_cfg:
                values.setdefault(
                    "provider", values.get("provider") or provider_cfg.name
                )
                values.setdefault(
                    "model_id",
                    values.get("model_id")
                    or provider_cfg.default_model
                    or DEFAULT_AGENT_MODEL,
                )
                # If api_key not provided by client, use provider config api_key
                if values.get("api_key") is None and getattr(
                    provider_cfg, "api_key", None
                ):
                    values["api_key"] = provider_cfg.api_key
            else:
                values.setdefault("provider", resolved_provider)
                values.setdefault(
                    "model_id", values.get("model_id") or DEFAULT_AGENT_MODEL
                )
        except Exception:
            # Fall back to constants if config manager unavailable
            values.setdefault(
                "provider", values.get("provider") or DEFAULT_MODEL_PROVIDER
            )
            values.setdefault("model_id", values.get("model_id") or DEFAULT_AGENT_MODEL)

        return values


class MarketType(str, Enum):
    """Market type for trading."""

    SPOT = "spot"
    FUTURE = "future"
    SWAP = "swap"  # Perpetual futures


class MarginMode(str, Enum):
    """Margin mode for leverage trading."""

    ISOLATED = "isolated"  # Isolated margin (逐仓)
    CROSS = "cross"  # Cross margin (全仓)


class ExchangeConfig(BaseModel):
    """Exchange configuration for trading."""

    exchange_id: Optional[str] = Field(
        default=None,
        description="Exchange identifier (e.g., 'okx', 'binance', 'bybit')",
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
    passphrase: Optional[str] = Field(
        default=None,
        description="API passphrase (required for some exchanges like OKX)",
    )
    testnet: bool = Field(
        default=False, description="Use testnet/sandbox mode for testing"
    )
    market_type: MarketType = Field(
        default=MarketType.SWAP,
        description="Market type: spot, future (delivery), or swap (perpetual)",
    )
    margin_mode: MarginMode = Field(
        default=MarginMode.CROSS,
        description="Margin mode: isolated (逐仓) or cross (全仓)",
    )
    fee_bps: float = Field(
        default=10.0,
        description="Trading fee in basis points (default 10 bps = 0.1%) for paper trading",
        gt=0,
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
        default=None, description="Saved prompt template id to use for this strategy"
    )
    prompt_text: Optional[str] = Field(
        default=None,
        description="Direct prompt text to use (overrides template_id if provided)",
    )
    custom_prompt: Optional[str] = Field(
        default=None, description="Custom prompt text to use alongside prompt_text"
    )

    cap_factor: float = Field(
        default=DEFAULT_CAP_FACTOR,
        description="Notional cap factor used by the composer to limit per-symbol exposure (e.g., 1.5)",
        gt=0,
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

    llm_model_config: LLMModelConfig = Field(
        default_factory=LLMModelConfig, description="AI model configuration"
    )
    exchange_config: ExchangeConfig = Field(
        default_factory=ExchangeConfig, description="Exchange configuration for trading"
    )
    trading_config: TradingConfig = Field(
        ..., description="Trading strategy configuration"
    )

    @model_validator(mode="before")
    @classmethod
    def _infer_market_type(cls, data):
        """Infer market_type from trading_config.max_leverage when not provided.

        Rule: if market_type is missing (not present in request), then
        - max_leverage <= 1.0 -> SPOT
        - max_leverage > 1.0  -> SWAP
        """
        if not isinstance(data, dict):
            return data
        values = dict(data)
        ex_cfg = dict(values.get("exchange_config") or {})
        # Only infer when market_type is not provided by the user
        mt_value = ex_cfg.get("market_type")
        mt_missing = (
            ("market_type" not in ex_cfg)
            or (mt_value is None)
            or (str(mt_value).strip() == "")
        )
        if mt_missing:
            tr_cfg = dict(values.get("trading_config") or {})
            ml_raw = tr_cfg.get("max_leverage")
            try:
                ml = (
                    float(ml_raw) if ml_raw is not None else float(DEFAULT_MAX_LEVERAGE)
                )
            except Exception:
                ml = float(DEFAULT_MAX_LEVERAGE)
            ex_cfg["market_type"] = MarketType.SPOT if ml <= 1.0 else MarketType.SWAP
            values["exchange_config"] = ex_cfg
        return values


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
        default=None,
        description=(
            "Optional metadata about the source window: keys MAY include interval, "
            "window_start_ts, window_end_ts (ms), count/num_points, and any feature "
            "family identifiers. Feature computers SHOULD populate these so downstream "
            "components can reason about freshness and coverage."
        ),
    )


class StrategyStatus(str, Enum):
    """High-level runtime status for strategies (for UI health dot)."""

    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class Constraints(BaseModel):
    """Typed constraints model used by the runtime and composer.

    Only includes guardrails used in Phase 1. Extend later in Phase 2.
    """

    max_positions: Optional[int] = Field(
        default=None,
        description="Maximum number of concurrent positions allowed for the strategy",
    )
    max_leverage: Optional[float] = Field(
        default=None,
        description="Maximum leverage allowed for the strategy (e.g., 2.0 means up to 2x).",
    )
    quantity_step: Optional[float] = Field(
        default=None,
        description="Minimum increment / step size for order quantities (in instrument units).",
    )
    min_trade_qty: Optional[float] = Field(
        default=None,
        description="Minimum trade quantity (in instrument units) allowed for a single order.",
    )
    max_order_qty: Optional[float] = Field(
        default=None,
        description="Maximum quantity allowed per single order (in instrument units).",
    )
    min_notional: Optional[float] = Field(
        default=None,
        description="Minimum order notional (in quote currency) required for an order to be placed.",
    )
    max_position_qty: Optional[float] = Field(
        default=None,
        description="Maximum absolute position quantity allowed for any single instrument (in instrument units).",
    )


class PositionSnapshot(BaseModel):
    """Current position snapshot for one instrument."""

    instrument: InstrumentRef
    quantity: float = Field(..., description="Position quantity (+long, -short)")
    avg_price: Optional[float] = Field(default=None, description="Average entry price")
    mark_price: Optional[float] = Field(
        default=None, description="Current mark/reference price for P&L calc"
    )
    unrealized_pnl: Optional[float] = Field(default=None, description="Unrealized PnL")
    unrealized_pnl_pct: Optional[float] = Field(
        default=None, description="Unrealized P&L as a percent of position value"
    )
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
    closed_ts: Optional[int] = Field(
        default=None, description="Close timestamp (ms) for recently closed positions"
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
    constraints: Optional[Constraints] = Field(
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
    buying_power: Optional[float] = Field(
        default=None,
        description="Buying power: max(0, equity * max_leverage - gross_exposure)",
    )


class LlmDecisionAction(str, Enum):
    """Normalized high-level action from LLM plan item.

    Semantics:
    - BUY/SELL: directional intent; final TradeSide is decided by delta (target - current)
    - NOOP: target equals current (delta == 0), no instruction should be emitted
    """

    BUY = "buy"
    SELL = "sell"
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
    leverage: Optional[float] = Field(
        default=None,
        description="Requested leverage multiple for this target (e.g., 1.0 = no leverage)."
        " Composer will clamp to allowed constraints.",
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
    rationale: Optional[str] = Field(
        default=None, description="Optional natural language rationale"
    )


class PriceMode(str, Enum):
    """Order price mode: market vs limit."""

    MARKET = "market"
    LIMIT = "limit"


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
    leverage: Optional[float] = Field(
        default=None,
        description="Leverage multiple to apply for this instruction (if supported).",
    )
    price_mode: PriceMode = Field(
        PriceMode.MARKET, description="Order price mode: market vs limit"
    )
    limit_price: Optional[float] = Field(default=None)
    max_slippage_bps: Optional[float] = Field(default=None)
    meta: Optional[Dict[str, str | float]] = Field(
        default=None, description="Optional metadata for auditing"
    )


class TxStatus(str, Enum):
    """Execution status of a submitted instruction."""

    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    ERROR = "error"


class TxResult(BaseModel):
    """Result of executing a TradeInstruction at a broker/exchange.

    This captures execution-side details such as fills, effective price,
    fees and slippage. The coordinator converts TxResult into TradeHistoryEntry.
    """

    instruction_id: str = Field(..., description="Originating instruction id")
    instrument: InstrumentRef
    side: TradeSide
    requested_qty: float = Field(..., description="Requested order quantity")
    filled_qty: float = Field(..., description="Filled quantity (<= requested)")
    avg_exec_price: Optional[float] = Field(
        default=None, description="Average execution price for the fills"
    )
    slippage_bps: Optional[float] = Field(
        default=None, description="Observed slippage in basis points"
    )
    fee_cost: Optional[float] = Field(
        default=None, description="Total fees charged in quote currency"
    )
    leverage: Optional[float] = Field(
        default=None, description="Leverage applied, if any"
    )
    status: TxStatus = Field(default=TxStatus.FILLED)
    reason: Optional[str] = Field(
        default=None, description="Message for rejects/errors"
    )
    meta: Optional[Dict[str, str | float]] = Field(default=None)


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
    # Total fees charged for this trade in quote currency (if available)
    fee_cost: Optional[float] = Field(
        default=None, description="Total fees charged in quote currency for this trade"
    )
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
    pnl_pct: Optional[float] = Field(
        default=None, description="P&L as percent of equity or initial capital"
    )
    unrealized_pnl: Optional[float] = Field(
        default=None, description="Unrealized P&L in quote CCY"
    )
    unrealized_pnl_pct: Optional[float] = Field(
        default=None, description="Unrealized P&L as a percent of position value"
    )
    last_updated_ts: Optional[int] = Field(default=None)


class StrategyStatusContent(BaseModel):
    """Content for strategy agent status component."""

    strategy_id: str
    status: StrategyStatus
