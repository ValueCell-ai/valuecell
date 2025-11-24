"""Asset data types and structures for the ValueCell platform.

This module defines the core data structures for representing financial assets
across different data sources and markets, with support for internationalization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class AssetType(str, Enum):
    """Enumeration of supported asset types.

    The other asset types are not supported yet.
    """

    STOCK = "stock"
    CRYPTO = "crypto"
    ETF = "etf"
    # BOND = "bond"
    # COMMODITY = "commodity"
    # FOREX = "forex"
    INDEX = "index"
    # MUTUAL_FUND = "mutual_fund"
    # OPTION = "option"
    # FUTURE = "future"


class Exchange(str, Enum):
    """Enumeration of supported exchanges."""

    NASDAQ = "NASDAQ"  # NASDAQ Market in the US
    NYSE = "NYSE"  # NYSE Market in the US
    AMEX = "AMEX"  # AMEX Market in the US
    SSE = "SSE"  # Shanghai Stock Exchange
    SZSE = "SZSE"  # Shenzhen Stock Exchange
    BSE = "BSE"  # Beijing Stock Exchange
    HKEX = "HKEX"  # Hong Kong Stock Exchange
    CRYPTO = "CRYPTO"  # Crypto Market


class MarketStatus(str, Enum):
    """Market status enumeration."""

    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    HALTED = "halted"
    UNKNOWN = "unknown"


class DataSource(str, Enum):
    """Supported data source providers."""

    YFINANCE = "yfinance"
    AKSHARE = "akshare"
    BAOSTOCK = "baostock"
    # TODO: Add other data sources later
    # TUSHARE = "tushare"
    # FINNHUB = "finnhub"
    # COINMARKETCAP = "coinmarketcap"
    # BINANCE = "binance"
    # ALPHA_VANTAGE = "alpha_vantage"


class Interval(str, Enum):
    """Supported intervals for historical data."""

    MINUTE = "m"
    HOUR = "h"
    DAY = "d"
    WEEK = "w"
    MONTH = "mo"
    YEAR = "y"


@dataclass
class MarketInfo:
    """Market information for an asset."""

    exchange: str  # Exchange identifier (e.g., "NASDAQ", "NYSE", "SSE", "CRYPTO")
    country: str  # ISO country code (e.g., "US", "CN", "HK")
    currency: str  # Currency code (e.g., "USD", "CNY", "HKD", "BTC")
    timezone: str  # Market timezone (e.g., "America/New_York", "Asia/Shanghai")
    trading_hours: Optional[Dict[str, str]] = None  # Trading hours info
    market_status: MarketStatus = MarketStatus.UNKNOWN


@dataclass
class LocalizedName:
    """Localized names for an asset in different languages."""

    names: Dict[str, str] = field(default_factory=dict)

    def get_name(self, language: str, fallback: str = "en-US") -> str:
        """Get localized name for a specific language.

        Args:
            language: Language code (e.g., 'zh-Hans', 'en-US')
            fallback: Fallback language if requested language not available

        Returns:
            Localized asset name
        """
        return self.names.get(language, self.names.get(fallback, ""))

    def set_name(self, language: str, name: str) -> None:
        """Set localized name for a specific language.

        Args:
            language: Language code
            name: Asset name in the specified language
        """
        self.names[language] = name

    def get_available_languages(self) -> List[str]:
        """Get list of available languages for this asset."""
        return list(self.names.keys())


class Asset(BaseModel):
    """Core asset data structure.

    This represents a financial asset in the ValueCell system with support
    for multiple data sources and internationalization.
    """

    # Core identification
    ticker: str = Field(
        ..., description="Standardized ticker format: [EXCHANGE]:[SYMBOL]"
    )
    asset_type: AssetType = Field(..., description="Type of financial asset")

    # Names and descriptions
    names: LocalizedName = Field(
        default_factory=LocalizedName, description="Localized asset names"
    )
    descriptions: Dict[str, str] = Field(
        default_factory=dict, description="Localized descriptions"
    )

    # Market information
    market_info: MarketInfo = Field(..., description="Market and exchange information")

    # Data source mappings
    source_mappings: Dict[DataSource, str] = Field(
        default_factory=dict,
        description="Mapping of data sources to their specific ticker formats",
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(
        default=True, description="Whether asset is currently tradable"
    )

    # Additional properties
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional asset properties"
    )

    @validator("ticker")
    def validate_ticker_format(cls, v):
        """Validate ticker format: EXCHANGE:SYMBOL"""
        if ":" not in v:
            raise ValueError("Ticker must be in format 'EXCHANGE:SYMBOL'")
        parts = v.split(":")
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise ValueError("Invalid ticker format. Expected 'EXCHANGE:SYMBOL'")
        return v.upper()

    def get_exchange(self) -> str:
        """Extract exchange from ticker."""
        return self.ticker.split(":")[0]

    def get_symbol(self) -> str:
        """Extract symbol from ticker."""
        return self.ticker.split(":")[1]

    def get_localized_name(self, language: str = "en-US") -> str:
        """Get asset name in specified language."""
        return self.names.get_name(language)

    def set_localized_name(self, language: str, name: str) -> None:
        """Set asset name for specified language."""
        self.names.set_name(language, name)
        self.updated_at = datetime.utcnow()

    def get_source_ticker(self, source: DataSource) -> Optional[str]:
        """Get ticker format for specific data source."""
        return self.source_mappings.get(source)

    def set_source_ticker(self, source: DataSource, ticker: str) -> None:
        """Set ticker format for specific data source."""
        self.source_mappings[source] = ticker
        self.updated_at = datetime.utcnow()

    def add_property(self, key: str, value: Any) -> None:
        """Add custom property to asset."""
        self.properties[key] = value
        self.updated_at = datetime.utcnow()

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get custom property value."""
        return self.properties.get(key, default)


@dataclass
class AssetPrice:
    """Real-time or historical price data for an asset."""

    ticker: str
    price: Decimal
    currency: str
    timestamp: datetime
    volume: Optional[Decimal] = None
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    source: Optional[DataSource] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "ticker": self.ticker,
            "price": float(self.price) if self.price else None,
            "currency": self.currency,
            "timestamp": self.timestamp.isoformat(),
            "volume": float(self.volume) if self.volume else None,
            "open_price": float(self.open_price) if self.open_price else None,
            "high_price": float(self.high_price) if self.high_price else None,
            "low_price": float(self.low_price) if self.low_price else None,
            "close_price": float(self.close_price) if self.close_price else None,
            "change": float(self.change) if self.change else None,
            "change_percent": float(self.change_percent)
            if self.change_percent
            else None,
            "market_cap": float(self.market_cap) if self.market_cap else None,
            "source": self.source.value if self.source else None,
        }


class WatchlistItem(BaseModel):
    """Individual item in a user's watchlist."""

    user_id: str = Field(..., description="User identifier")
    ticker: str = Field(..., description="Asset ticker in standard format")
    added_at: datetime = Field(
        default_factory=datetime.utcnow, description="When added to watchlist"
    )
    order: int = Field(default=0, description="Display order in watchlist")
    notes: str = Field(default="", description="User's personal notes about this asset")
    alerts: Dict[str, Any] = Field(
        default_factory=dict, description="Price alerts and notifications"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Watchlist(BaseModel):
    """User's complete watchlist."""

    user_id: str = Field(..., description="User identifier")
    name: str = Field(default="My Watchlist", description="Watchlist name")
    description: str = Field(default="", description="Watchlist description")
    items: List[WatchlistItem] = Field(
        default_factory=list, description="Assets in watchlist"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_default: bool = Field(
        default=True, description="Whether this is the default watchlist"
    )
    is_public: bool = Field(
        default=False, description="Whether watchlist is publicly visible"
    )

    def add_asset(
        self, ticker: str, notes: str = "", order: Optional[int] = None
    ) -> None:
        """Add asset to watchlist."""
        # Check if asset already exists
        for item in self.items:
            if item.ticker == ticker:
                return  # Asset already in watchlist

        # Determine order
        if order is None:
            order = len(self.items)

        # Create new watchlist item
        item = WatchlistItem(
            user_id=self.user_id, ticker=ticker, order=order, notes=notes
        )

        self.items.append(item)
        self.updated_at = datetime.utcnow()

    def remove_asset(self, ticker: str) -> bool:
        """Remove asset from watchlist. Returns True if removed, False if not found."""
        for i, item in enumerate(self.items):
            if item.ticker == ticker:
                del self.items[i]
                self.updated_at = datetime.utcnow()
                return True
        return False

    def reorder_assets(self, ticker_order: List[str]) -> None:
        """Reorder assets according to provided ticker list."""
        # Create a mapping of ticker to new order
        order_map = {ticker: i for i, ticker in enumerate(ticker_order)}

        # Update order for existing items
        for item in self.items:
            if item.ticker in order_map:
                item.order = order_map[item.ticker]

        # Sort items by order
        self.items.sort(key=lambda x: x.order)
        self.updated_at = datetime.utcnow()

    def get_tickers(self) -> List[str]:
        """Get list of all tickers in watchlist."""
        return [item.ticker for item in sorted(self.items, key=lambda x: x.order)]

    def get_item(self, ticker: str) -> Optional[WatchlistItem]:
        """Get watchlist item by ticker."""
        for item in self.items:
            if item.ticker == ticker:
                return item
        return None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AssetSearchResult(BaseModel):
    """Search result for asset lookup."""

    ticker: str = Field(..., description="Standardized ticker")
    asset_type: AssetType = Field(..., description="Asset type")
    names: Dict[str, str] = Field(..., description="Asset names in different languages")
    exchange: str = Field(..., description="Exchange name")
    country: str = Field(..., description="Country code")

    # Optional fields for enhanced search results
    currency: Optional[str] = Field(default=None, description="Currency code")
    market_status: Optional[MarketStatus] = Field(
        default=None, description="Market status"
    )
    relevance_score: float = Field(
        default=0.5, description="Search relevance score (0-1)"
    )

    def get_display_name(self, language: str = "en-US") -> str:
        """Get display name for specified language."""
        return self.names.get(language, self.names.get("en-US", self.ticker))


class AssetSearchQuery(BaseModel):
    """Asset search query parameters."""

    query: str = Field(..., description="Search query string")
    limit: int = Field(default=10, description="Maximum number of results")

    @validator("limit")
    def validate_limit(cls, v):
        if v <= 0 or v > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        return v
