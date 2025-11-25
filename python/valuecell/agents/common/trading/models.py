from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from valuecell.utils.ts import get_current_timestamp_ms

from .constants import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_CAP_FACTOR,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_MAX_LEVERAGE,
    DEFAULT_MAX_POSITIONS,
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
    """Low-level execution side (exchange primitive).

    This remains distinct from `TradeDecisionAction` which encodes *intent* at a
    position semantic level (open_long/close_short/etc). TradeSide is kept for:
    - direct mapping to exchange APIs that require BUY/SELL
    - conveying slippage/fee direction in execution records

    Removal consideration: if the pipeline fully normalizes around
    TradeDecisionAction -> (final target delta), we can derive side on the fly:
        OPEN_LONG, CLOSE_SHORT -> BUY
        OPEN_SHORT, CLOSE_LONG -> SELL
    For now we keep it explicit to avoid recomputation and ease auditing.
    """

    BUY = "BUY"
    SELL = "SELL"


class StrategyType(str, Enum):
    """Strategy type selection for StrategyAgent variants.

    - PROMPT: Prompt-based strategy agent
    - GRID: Grid strategy agent
    """

    PROMPT = "PromptBasedStrategy"
    GRID = "GridStrategy"


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

    ISOLATED = "isolated"  # Isolated margin
    CROSS = "cross"  # Cross margin


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
    wallet_address: Optional[str] = Field(
        default=None,
        description="Wallet address (required for Hyperliquid)",
    )
    private_key: Optional[str] = Field(
        default=None,
        description="Private key (required for Hyperliquid)",
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
        description="Margin mode: isolated or cross",
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
    strategy_type: Optional[StrategyType] = Field(
        default=StrategyType.PROMPT,
        description="Strategy type: 'prompt based strategy' or 'grid strategy'",
    )
    strategy_id: Optional[str] = Field(
        default=None,
        description="Reuse existing strategy id to continue execution (resume semantics without extra flags)",
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
    # Grid parameters are model-decided at runtime; no user-configurable grid_* fields.

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one symbol is required")
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
    # quote_ccy: Optional[str] = Field(
    #     default=None, description="Quote currency (e.g., USDT)"
    # )


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


class GridParamAdvice(BaseModel):
    """LLM-advised grid parameter set.

    Advisor should return sensible values within typical ranges:
    - grid_step_pct: 0.0005 ~ 0.01
    - grid_max_steps: 1 ~ 5
    - grid_base_fraction: 0.03 ~ 0.10
    """

    ts: int = Field(..., description="Advice timestamp in ms")
    grid_step_pct: float = Field(..., gt=0)
    grid_max_steps: int = Field(..., gt=0)
    grid_base_fraction: float = Field(..., gt=0)
    # Optional zone and discretization
    grid_lower_pct: Optional[float] = Field(default=None, gt=0)
    grid_upper_pct: Optional[float] = Field(default=None, gt=0)
    grid_count: Optional[int] = Field(default=None, gt=0)
    advisor_rationale: Optional[str] = Field(
        default=None,
        description="Model-provided reasoning explaining how grid parameters were chosen",
    )


CommonKeyType = str
CommonValueType = float | str | int


class FeatureVector(BaseModel):
    """Computed features for a single instrument at a point in time."""

    ts: int = Field(
        ...,
        description="Feature vector timestamp in ms",
    )
    instrument: InstrumentRef
    values: Dict[CommonKeyType, CommonValueType | List[CommonValueType]] = Field(
        default_factory=dict, description="Feature name to numeric value"
    )
    meta: Optional[Dict[CommonKeyType, CommonValueType]] = Field(
        default=None,
        description=(
            "Optional metadata about the source window: keys MAY include interval, "
            "window_start_ts, window_end_ts (ms), count/num_points, and any feature "
            "family identifiers. Feature computers SHOULD populate these so downstream "
            "components can reason about freshness and coverage."
        ),
    )


class StrategyStatus(str, Enum):
    """High-level runtime status for strategies (simplified).

    Removed legacy PAUSED and ERROR states; cancellation or errors now finalize
    to STOPPED with error context stored separately (e.g., strategy_metadata).
    """

    RUNNING = "running"
    STOPPED = "stopped"


class StopReason(str, Enum):
    """Canonical stop reasons recorded in strategy metadata.

    Stored values are the enum `.value` strings so other services (DB, repos)
    can compare without importing the enum if necessary, but code should
    prefer using the enum when available.
    """

    NORMAL_EXIT = "normal_exit"
    CANCELLED = "cancelled"
    ERROR = "error"
    ERROR_CLOSING_POSITIONS = "error_closing_positions"


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
    account_balance: float = Field(
        ..., description="Account cash balance in quote currency"
    )
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
    total_realized_pnl: Optional[float] = Field(
        default=None, description="Sum of realized PnL from closed position deltas"
    )
    buying_power: Optional[float] = Field(
        default=None,
        description="Buying power: max(0, equity * max_leverage - gross_exposure)",
    )
    free_cash: Optional[float] = Field(
        default=None,
        description=(
            "Approx available funds without tracking margin_used explicitly. "
            "Definition: free_cash = max(0, equity - sum_i(notional_i / L_i)), "
            "where equity = total_value (if provided) else (cash + total_unrealized_pnl or 0). "
            "For spot/no-leverage positions L_i = 1; for leveraged positions L_i is each position's"
            " effective leverage if available, otherwise falls back to constraints.max_leverage."
        ),
    )


class TradeDecisionAction(str, Enum):
    """Position-oriented high-level actions produced by the plan.

    Semantics:
    - OPEN_LONG: open/increase long; if currently short, flatten then open long
    - OPEN_SHORT: open/increase short; if currently long, flatten then open short
    - CLOSE_LONG: reduce/close long toward 0
    - CLOSE_SHORT: reduce/close short toward 0
    - NOOP: no operation
    """

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    NOOP = "noop"


def derive_side_from_action(
    action: Optional[TradeDecisionAction],
) -> Optional["TradeSide"]:
    """Derive execution side (BUY/SELL) from a high-level action.

    Returns None for non-order actions (e.g., noop, future amend/cancel types).
    """
    if action is None:
        return None
    if action in (TradeDecisionAction.OPEN_LONG, TradeDecisionAction.CLOSE_SHORT):
        return TradeSide.BUY
    if action in (TradeDecisionAction.OPEN_SHORT, TradeDecisionAction.CLOSE_LONG):
        return TradeSide.SELL
    # NOOP or future adjust/cancel actions: no executable side
    return None


class TradeDecisionItem(BaseModel):
    """Trade plan item. Interprets target_qty as operation size (magnitude).

    Unlike the previous "final target position" semantics, target_qty here
    is the size to operate (same unit as position quantity). The composer
    derives the final target from the action and current quantity.
    """

    instrument: InstrumentRef
    action: TradeDecisionAction
    target_qty: float = Field(
        ...,
        description="Operation size for this action (units), e.g., open/close long/short",
    )
    leverage: Optional[float] = Field(
        default=None,
        description="Requested leverage multiple for this action (e.g., 1.0 = no leverage). The composer clamps to constraints.",
    )
    confidence: Optional[float] = Field(
        default=None, description="Optional confidence score [0,1]"
    )
    rationale: Optional[str] = Field(
        default=None, description="Optional natural language rationale"
    )

    # TODO: Remove this validator when the model supports InstrumentRef.
    @model_validator(mode="before")
    @classmethod
    def _normalize_instrument(cls, data):
        """Normalize instrument field: allow string shorthand for InstrumentRef.

        Some LLMs return instrument as a plain string (e.g., "ETH/USDT") instead
        of an object {"symbol": "ETH/USDT"}. This validator handles both formats.
        """
        if not isinstance(data, dict):
            return data
        values = dict(data)
        instrument = values.get("instrument")
        if isinstance(instrument, str):
            values["instrument"] = {"symbol": instrument}
        return values


class TradePlanProposal(BaseModel):
    """Structured output before rule normalization."""

    ts: Optional[int] = Field(
        default_factory=get_current_timestamp_ms,
        description="Proposal timestamp in ms (if available)",
    )
    items: List[TradeDecisionItem] = Field(default_factory=list)
    rationale: Optional[str] = Field(
        default=None, description="Optional natural language rationale"
    )


class PriceMode(str, Enum):
    """Order price mode: market vs limit."""

    MARKET = "market"
    LIMIT = "limit"


class TradeInstruction(BaseModel):
    """Executable instruction emitted by the composer after normalization.

    Includes optional action for executor dispatch (open_long/open_short/close_long/close_short/noop).
    """

    instruction_id: str = Field(
        ..., description="Deterministic id for idempotency (e.g., compose_id+symbol)"
    )
    compose_id: str = Field(
        ..., description="Decision cycle id to correlate instructions and history"
    )
    instrument: InstrumentRef
    action: Optional[TradeDecisionAction] = Field(
        default=None,
        description="High-level intent action for dispatch ('open_long'|'open_short'|'close_long'|'close_short'|'noop')",
    )
    side: TradeSide  # Derived execution direction (BUY/SELL) consistent with action
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
    meta: Optional[Dict[str, str | float | bool]] = Field(
        default=None, description="Optional metadata for auditing"
    )

    @model_validator(mode="after")
    def _validate_action_side_alignment(self):
        """Ensure action (if provided) aligns with the executable side.

        Mapping (state-independent after normalization):
          - OPEN_LONG  -> BUY
          - CLOSE_SHORT-> BUY
          - OPEN_SHORT -> SELL
          - CLOSE_LONG -> SELL
          - NOOP       -> should not be emitted as an instruction
        """
        act = self.action
        if act is None:
            return self
        try:
            if act == TradeDecisionAction.NOOP:
                # Composer should not emit NOOP instructions; tolerate in lenient mode
                return self
            if act in (TradeDecisionAction.OPEN_LONG, TradeDecisionAction.CLOSE_SHORT):
                expected = TradeSide.BUY
            elif act in (
                TradeDecisionAction.OPEN_SHORT,
                TradeDecisionAction.CLOSE_LONG,
            ):
                expected = TradeSide.SELL
            else:
                return self
            if self.side != expected:
                raise ValueError(
                    f"TradeInstruction.action={act} conflicts with side={self.side}; expected {expected}"
                )
        except Exception:
            # Be conservative: do not block pipeline on validator edge cases
            return self
        return self


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
    side: TradeSide  # Echo of execution direction for auditing
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
    meta: Optional[Dict[str, str | float | bool]] = Field(default=None)


class MetricPoint(BaseModel):
    """Generic time-value point, used for value history charts."""

    ts: int
    value: float


class PortfolioValueSeries(BaseModel):
    """Series for portfolio total value over time (for performance charts)."""

    strategy_id: Optional[str] = Field(default=None)
    points: List[MetricPoint] = Field(default_factory=list)


MarketSnapShotType = Dict[str, Dict[str, Any]]


class ComposeContext(BaseModel):
    """Context assembled for the composer."""

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
    avg_exec_price: Optional[float] = Field(
        default=None, description="Average execution price for fills"
    )
    notional_entry: Optional[float] = Field(default=None)
    notional_exit: Optional[float] = Field(default=None)
    entry_ts: Optional[int] = Field(default=None, description="Entry timestamp ms")
    exit_ts: Optional[int] = Field(default=None, description="Exit timestamp ms")
    trade_ts: Optional[int] = Field(default=None, description="Trade timestamp in ms")
    holding_ms: Optional[int] = Field(default=None, description="Holding time in ms")
    unrealized_pnl: Optional[float] = Field(
        default=None, description="Unrealized PnL in quote currency"
    )
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
    sharpe_ratio: Optional[float] = Field(
        default=None,
        description=(
            "Sharpe Ratio computed from recent equity curve. "
            "Formula: (avg_return - risk_free_rate) / std_dev_returns. "
            "Interpretation: <0 losing; 0-1 positive but volatile; "
            "1-2 good; >2 excellent risk-adjusted performance."
        ),
    )


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
    total_value: Optional[float] = Field(
        default=None,
        description="Total portfolio value (equity) including cash and positions",
    )
    last_updated_ts: Optional[int] = Field(default=None)


class StrategyStatusContent(BaseModel):
    """Content for strategy agent status component."""

    strategy_id: str
    status: StrategyStatus
    # Optional stop reason and human-readable detail for terminal states/errors
    stop_reason: Optional[StopReason] = Field(
        default=None, description="Canonical stop reason for the strategy"
    )
    stop_reason_detail: Optional[str] = Field(
        default=None,
        description="Optional human-readable detail about stop reason or error",
    )


class ComposeResult(BaseModel):
    """Result of a compose operation."""

    instructions: List[TradeInstruction]
    rationale: Optional[str] = None


class FeaturesPipelineResult(BaseModel):
    """Result of running a features pipeline."""

    features: List[FeatureVector]


@dataclass
class DecisionCycleResult:
    """Outcome of a single decision cycle."""

    compose_id: str
    timestamp_ms: int
    cycle_index: int
    rationale: Optional[str]
    strategy_summary: StrategySummary
    instructions: List[TradeInstruction]
    trades: List[TradeHistoryEntry]
    history_records: List[HistoryRecord]
    digest: TradeDigest
    portfolio_view: PortfolioView
