"""Data models and enumerations for auto trading agent"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .constants import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_MAX_POSITIONS,
    DEFAULT_RISK_PER_TRADE,
    MAX_SYMBOLS,
)

SUPPORTED_EXCHANGES = {"paper", "okx"}
SUPPORTED_NETWORKS = {"testnet", "mainnet", "demo", "beta", "local", "paper"}


class TradeAction(str, Enum):
    """Trade action enumeration"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class TradeType(str, Enum):
    """Trade type enumeration"""

    LONG = "long"
    SHORT = "short"


class TradingRequest(BaseModel):
    """Auto trading request model for parsing natural language queries"""

    crypto_symbols: List[str] = Field(
        ...,
        description="List of crypto symbols to trade (e.g., ['BTC-USD', 'ETH-USD'])",
    )
    initial_capital: Optional[float] = Field(
        default=DEFAULT_INITIAL_CAPITAL,
        description="Initial capital for trading in USD",
        gt=0,
    )
    use_ai_signals: Optional[bool] = Field(
        default=False,
        description="Whether to use AI-enhanced trading signals",
    )
    agent_models: Optional[List[str]] = Field(
        default=[DEFAULT_AGENT_MODEL],
        description="List of model IDs for trading decisions - one instance per model",
    )
    exchange: Optional[str] = Field(
        default=None,
        description="Exchange adapter to use (paper or okx)",
    )
    exchange_network: Optional[str] = Field(
        default=None,
        description="Target network for the exchange (testnet, mainnet, etc.)",
    )
    allow_live_trading: Optional[bool] = Field(
        default=None,
        description="Explicit confirmation toggle for mainnet trading",
    )
    okx_td_mode: Optional[str] = Field(
        default=None,
        description="OKX trading mode (cash, cross, isolated); defaults to cash",
    )

    @field_validator("crypto_symbols")
    @classmethod
    def validate_symbols(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one crypto symbol is required")
        if len(v) > MAX_SYMBOLS:
            raise ValueError(f"Maximum {MAX_SYMBOLS} symbols allowed")
        # Normalize symbols to uppercase
        return [s.upper() for s in v]

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, value):
        if value is None:
            return value
        lowered = value.lower()
        if lowered not in SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange '{value}'")
        return lowered

    @field_validator("exchange_network")
    @classmethod
    def validate_exchange_network(cls, value):
        if value is None:
            return value
        lowered = value.lower()
        if lowered not in SUPPORTED_NETWORKS:
            raise ValueError(f"Unsupported exchange network '{value}'")
        return lowered


class AutoTradingConfig(BaseModel):
    """Configuration for auto trading agent"""

    initial_capital: float = Field(..., description="Initial capital for trading", gt=0)
    crypto_symbols: List[str] = Field(
        ...,
        description="List of crypto symbols to trade (max 10)",
        max_length=MAX_SYMBOLS,
    )
    check_interval: int = Field(
        default=60,
        description="Check interval in seconds",
        gt=0,
    )
    risk_per_trade: float = Field(
        default=DEFAULT_RISK_PER_TRADE,
        description="Risk per trade as percentage of capital",
        gt=0,
        lt=1,
    )
    max_positions: int = Field(
        default=DEFAULT_MAX_POSITIONS,
        description="Maximum number of concurrent positions",
        gt=0,
    )
    agent_model: str = Field(
        default=DEFAULT_AGENT_MODEL,
        description="Model ID for AI-enhanced trading decisions (single model per instance)",
    )
    agent_provider: Optional[str] = Field(
        default=None,
        description="Provider name (null = auto-detect from config system)",
    )
    use_ai_signals: bool = Field(
        default=False,
        description="Whether to use AI model for enhanced signal generation",
    )
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key for AI model access",
    )
    exchange: str = Field(
        default="paper",
        description="Exchange adapter to use (paper or okx)",
    )
    exchange_network: str = Field(
        default="testnet",
        description="Exchange network identifier (testnet, mainnet, etc.)",
    )
    allow_live_trading: bool = Field(
        default=False,
        description="Must be true to enable mainnet order placement",
    )
    okx_api_key: Optional[str] = Field(
        default=None,
        description="OKX API key for REST access",
        repr=False,
    )
    okx_api_secret: Optional[str] = Field(
        default=None,
        description="OKX API secret",
        repr=False,
    )
    okx_api_passphrase: Optional[str] = Field(
        default=None,
        description="OKX API passphrase",
        repr=False,
    )
    okx_margin_mode: str = Field(
        default="cross",
        description="OKX trading mode (contracts cross by default; use 'cash' for SPOT)",
    )
    okx_use_server_time: bool = Field(
        default=False,
        description="Sync with OKX server time when placing orders",
    )

    @field_validator("crypto_symbols")
    @classmethod
    def validate_symbols(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one crypto symbol is required")
        if len(v) > MAX_SYMBOLS:
            raise ValueError(f"Maximum {MAX_SYMBOLS} symbols allowed")
        # Normalize symbols to uppercase
        return [s.upper() for s in v]

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, value: str) -> str:
        lowered = value.lower()
        if lowered not in SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange '{value}'")
        return lowered

    @field_validator("exchange_network")
    @classmethod
    def validate_network(cls, value: str) -> str:
        lowered = value.lower()
        if lowered not in SUPPORTED_NETWORKS:
            raise ValueError(f"Unsupported exchange network '{value}'")
        return lowered


class Position(BaseModel):
    """Trading position model"""

    symbol: str
    entry_price: float
    quantity: float
    entry_time: datetime
    trade_type: TradeType
    notional: float


class CashManagement(BaseModel):
    """Cash management tracking"""

    total_cash: float = Field(..., description="Total available cash for trading")
    initial_cash: float = Field(..., description="Initial cash allocated")
    reserved_cash: float = Field(
        default=0, description="Cash reserved for pending positions"
    )
    available_cash: float = Field(
        ..., description="Available cash for new trades (total_cash - reserved_cash)"
    )
    cash_in_trades: float = Field(
        default=0, description="Cash currently deployed in open positions"
    )

    class Config:
        """Pydantic config"""

        frozen = False


class TechnicalIndicators(BaseModel):
    """Technical indicators for a symbol"""

    symbol: str
    timestamp: datetime
    close_price: float
    volume: float
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    rsi: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    ema_50: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None


class TradeHistoryRecord(BaseModel):
    """Single trade execution history record"""

    timestamp: datetime = Field(..., description="Trade execution timestamp")
    symbol: str = Field(..., description="Trading symbol")
    action: str = Field(..., description="Trade action: opened or closed")
    trade_type: str = Field(..., description="Trade type: long or short")
    price: float = Field(..., description="Execution price")
    quantity: float = Field(..., description="Trade quantity")
    notional: float = Field(..., description="Trade notional value")
    pnl: Optional[float] = Field(None, description="P&L for closed positions")
    portfolio_value_after: float = Field(
        ..., description="Portfolio value after this trade"
    )
    cash_after: float = Field(..., description="Available cash after this trade")


class PositionHistorySnapshot(BaseModel):
    """Position snapshot at a point in time"""

    timestamp: datetime = Field(..., description="Snapshot timestamp")
    symbol: str = Field(..., description="Trading symbol")
    quantity: float = Field(..., description="Position quantity")
    entry_price: float = Field(..., description="Entry price")
    current_price: float = Field(..., description="Current market price")
    trade_type: str = Field(..., description="Trade type: long or short")
    unrealized_pnl: float = Field(..., description="Unrealized P&L")
    notional: float = Field(..., description="Position notional value")


class PortfolioValueSnapshot(BaseModel):
    """Portfolio value snapshot at a point in time"""

    timestamp: datetime = Field(..., description="Snapshot timestamp")
    total_value: float = Field(..., description="Total portfolio value")
    cash: float = Field(..., description="Available cash")
    cash_in_trades: float = Field(
        ..., description="Cash currently deployed in positions"
    )
    positions_value: float = Field(..., description="Value of open positions")
    positions_count: int = Field(..., description="Number of open positions")
    total_pnl: float = Field(..., description="Total unrealized P&L")


class TradingInstanceData(BaseModel):
    """Complete data for a trading instance"""

    instance_id: str = Field(..., description="Unique instance ID")
    session_id: str = Field(..., description="Session ID")
    config: AutoTradingConfig = Field(..., description="Trading configuration")
    created_at: datetime = Field(..., description="Instance creation time")
    active: bool = Field(..., description="Whether instance is active")

    # Historical data
    trade_history: List[TradeHistoryRecord] = Field(
        default_factory=list, description="All trade executions"
    )
    position_history: List[PositionHistorySnapshot] = Field(
        default_factory=list, description="Position snapshots over time"
    )
    portfolio_history: List[PortfolioValueSnapshot] = Field(
        default_factory=list, description="Portfolio value over time"
    )

    # Current state
    current_positions: List[Position] = Field(
        default_factory=list, description="Current open positions"
    )
    current_capital: float = Field(..., description="Current available capital")
    current_portfolio_value: float = Field(
        ..., description="Current total portfolio value"
    )

    # Statistics
    check_count: int = Field(default=0, description="Number of market checks performed")
    last_check_time: Optional[datetime] = Field(
        None, description="Last market check time"
    )
    total_trades: int = Field(default=0, description="Total number of trades executed")
