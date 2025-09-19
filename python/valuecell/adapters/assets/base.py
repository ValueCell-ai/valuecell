"""Base classes and interfaces for asset data adapters.

This module defines the abstract base classes that all data source adapters
must implement to ensure consistent behavior across different providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .types import (
    Asset,
    AssetPrice,
    AssetSearchResult,
    AssetSearchQuery,
    DataSource,
    AssetType,
)

logger = logging.getLogger(__name__)


class TickerConverter:
    """Utility class for converting between internal ticker format and data source formats."""

    def __init__(self):
        """Initialize ticker converter with mapping rules."""
        # Mapping from internal exchange codes to data source specific formats
        self.exchange_mappings: Dict[DataSource, Dict[str, str]] = {
            DataSource.YFINANCE: {
                "NASDAQ": "",  # NASDAQ stocks don't need suffix in yfinance
                "NYSE": "",  # NYSE stocks don't need suffix in yfinance
                "SSE": ".SS",  # Shanghai Stock Exchange
                "SZSE": ".SZ",  # Shenzhen Stock Exchange
                "HKEX": ".HK",  # Hong Kong Exchange
                "TSE": ".T",  # Tokyo Stock Exchange
            },
            DataSource.TUSHARE: {
                "SSE": ".SH",  # Shanghai Stock Exchange in TuShare
                "SZSE": ".SZ",  # Shenzhen Stock Exchange in TuShare
            },
            DataSource.AKSHARE: {
                "SSE": "",  # AKShare uses plain symbols for Chinese stocks
                "SZSE": "",  # AKShare uses plain symbols for Chinese stocks
                "BSE": "",  # Beijing Stock Exchange
            },
            DataSource.FINNHUB: {
                "NASDAQ": "",  # Finnhub uses plain symbols for US stocks
                "NYSE": "",  # Finnhub uses plain symbols for US stocks
                "AMEX": "",  # American Stock Exchange
                "HKEX": ".HK",  # Hong Kong stocks need .HK suffix
                "TSE": ".T",  # Tokyo Stock Exchange
                "LSE": ".L",  # London Stock Exchange
                "XETRA": ".DE",  # German Exchange
            },
            DataSource.COINMARKETCAP: {
                "CRYPTO": "",  # Crypto symbols are used as-is
            },
        }

        # Reverse mappings for converting back to internal format
        self.reverse_mappings: Dict[DataSource, Dict[str, str]] = {}
        for source, mappings in self.exchange_mappings.items():
            self.reverse_mappings[source] = {v: k for k, v in mappings.items() if v}

    def to_source_format(self, internal_ticker: str, source: DataSource) -> str:
        """Convert internal ticker format to data source specific format.

        Args:
            internal_ticker: Ticker in internal format (e.g., "NASDAQ:AAPL")
            source: Target data source

        Returns:
            Ticker in data source specific format (e.g., "AAPL" for yfinance)
        """
        try:
            exchange, symbol = internal_ticker.split(":", 1)

            # Special handling for crypto tickers in yfinance
            if exchange == "CRYPTO" and source == DataSource.YFINANCE:
                # Map common crypto symbols to yfinance format
                crypto_mapping = {
                    "BTC": "BTC-USD",
                    "ETH": "ETH-USD",
                    "ADA": "ADA-USD",
                    "DOT": "DOT-USD",
                    "SOL": "SOL-USD",
                    "MATIC": "MATIC-USD",
                    "LINK": "LINK-USD",
                    "UNI": "UNI-USD",
                    "AVAX": "AVAX-USD",
                    "ATOM": "ATOM-USD",
                }
                return crypto_mapping.get(symbol, f"{symbol}-USD")

            # Special handling for Hong Kong stocks in yfinance
            if exchange == "HKEX" and source == DataSource.YFINANCE:
                # Hong Kong stock codes need to be in proper format
                # e.g., "700" -> "0700.HK", "00700" -> "0700.HK", "1234" -> "1234.HK"
                if symbol.isdigit():
                    # Remove leading zeros first, then pad to 4 digits
                    clean_symbol = str(int(symbol))  # Remove leading zeros
                    padded_symbol = clean_symbol.zfill(4)  # Pad to 4 digits
                    return f"{padded_symbol}.HK"
                else:
                    # For non-numeric symbols, use as-is with .HK suffix
                    return f"{symbol}.HK"

            if source not in self.exchange_mappings:
                logger.warning(f"No mapping found for data source: {source}")
                return symbol

            suffix = self.exchange_mappings[source].get(exchange, "")
            return f"{symbol}{suffix}"

        except ValueError:
            logger.error(f"Invalid ticker format: {internal_ticker}")
            return internal_ticker

    def to_internal_format(
        self,
        source_ticker: str,
        source: DataSource,
        default_exchange: Optional[str] = None,
    ) -> str:
        """Convert data source ticker to internal format.

        Args:
            source_ticker: Ticker in data source format (e.g., "000001.SZ")
            source: Source data provider
            default_exchange: Default exchange if cannot be determined from ticker

        Returns:
            Ticker in internal format (e.g., "SZSE:000001")
        """
        try:
            # Special handling for Hong Kong stocks from yfinance
            if source == DataSource.YFINANCE and source_ticker.endswith(".HK"):
                symbol = source_ticker[:-3]  # Remove .HK suffix
                # Remove leading zeros for internal format (0700 -> 700)
                if symbol.isdigit():
                    symbol = str(int(symbol))  # This removes leading zeros
                return f"HKEX:{symbol}"

            # Special handling for crypto from yfinance
            if source == DataSource.YFINANCE and "-USD" in source_ticker:
                crypto_symbol = source_ticker.replace("-USD", "")
                return f"CRYPTO:{crypto_symbol}"

            # Check for known suffixes
            if source in self.reverse_mappings:
                for suffix, exchange in self.reverse_mappings[source].items():
                    if source_ticker.endswith(suffix):
                        symbol = (
                            source_ticker[: -len(suffix)] if suffix else source_ticker
                        )
                        return f"{exchange}:{symbol}"

            # If no suffix found and default exchange provided
            if default_exchange:
                return f"{default_exchange}:{source_ticker}"

            # For crypto and other assets without clear exchange mapping
            if source == DataSource.COINMARKETCAP:
                return f"CRYPTO:{source_ticker}"

            # Fallback to using the source as exchange
            return f"{source.value.upper()}:{source_ticker}"

        except Exception as e:
            logger.error(f"Error converting ticker {source_ticker}: {e}")
            return f"UNKNOWN:{source_ticker}"

    def get_supported_exchanges(self, source: DataSource) -> List[str]:
        """Get list of supported exchanges for a data source."""
        return list(self.exchange_mappings.get(source, {}).keys())


class BaseDataAdapter(ABC):
    """Abstract base class for all data source adapters."""

    def __init__(self, source: DataSource, api_key: Optional[str] = None, **kwargs):
        """Initialize adapter with data source and configuration.

        Args:
            source: Data source identifier
            api_key: API key for the data source (if required)
            **kwargs: Additional configuration parameters
        """
        self.source = source
        self.api_key = api_key
        self.config = kwargs
        self.converter = TickerConverter()
        self.logger = logging.getLogger(f"{__name__}.{source.value}")

        # Initialize adapter-specific configuration
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize adapter-specific configuration and connections."""
        pass

    @abstractmethod
    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets matching the query criteria.

        Args:
            query: Search query parameters

        Returns:
            List of matching assets
        """
        pass

    @abstractmethod
    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed information about a specific asset.

        Args:
            ticker: Asset ticker in internal format

        Returns:
            Asset information or None if not found
        """
        pass

    @abstractmethod
    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data for an asset.

        Args:
            ticker: Asset ticker in internal format

        Returns:
            Current price data or None if not available
        """
        pass

    @abstractmethod
    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[AssetPrice]:
        """Get historical price data for an asset.

        Args:
            ticker: Asset ticker in internal format
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (e.g., "1d", "1h", "5m")

        Returns:
            List of historical price data
        """
        pass

    def get_multiple_prices(
        self, tickers: List[str]
    ) -> Dict[str, Optional[AssetPrice]]:
        """Get real-time prices for multiple assets.

        Args:
            tickers: List of asset tickers in internal format

        Returns:
            Dictionary mapping tickers to price data
        """
        results = {}
        for ticker in tickers:
            try:
                results[ticker] = self.get_real_time_price(ticker)
            except Exception as e:
                self.logger.error(f"Error fetching price for {ticker}: {e}")
                results[ticker] = None
        return results

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if a ticker format is supported by this adapter.

        Args:
            ticker: Ticker in internal format

        Returns:
            True if ticker is valid for this adapter
        """
        try:
            exchange, _ = ticker.split(":", 1)
            supported_exchanges = self.converter.get_supported_exchanges(self.source)
            return exchange in supported_exchanges
        except ValueError:
            return False

    def convert_to_source_ticker(self, internal_ticker: str) -> str:
        """Convert internal ticker to data source format."""
        return self.converter.to_source_format(internal_ticker, self.source)

    def convert_to_internal_ticker(
        self, source_ticker: str, default_exchange: Optional[str] = None
    ) -> str:
        """Convert data source ticker to internal format."""
        return self.converter.to_internal_format(
            source_ticker, self.source, default_exchange
        )

    def is_market_open(self, exchange: str) -> bool:
        """Check if a specific market is currently open.

        Args:
            exchange: Exchange identifier

        Returns:
            True if market is open, False otherwise
        """
        # This is a basic implementation - subclasses should override
        # with more accurate market hours checking
        now = datetime.utcnow()
        hour = now.hour

        # Basic US market hours (9:30 AM - 4:00 PM EST = 14:30 - 21:00 UTC)
        if exchange in ["NASDAQ", "NYSE"]:
            return 14 <= hour < 21

        # Basic Chinese market hours (9:30 AM - 3:00 PM CST = 1:30 - 7:00 UTC)
        elif exchange in ["SSE", "SZSE"]:
            return 1 <= hour < 7

        # For crypto markets, assume always open
        elif exchange in ["CRYPTO"]:
            return True

        return False

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get list of asset types supported by this adapter."""
        # Default implementation - subclasses should override
        return [AssetType.STOCK]

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the data adapter.

        Returns:
            Dictionary containing health status information
        """
        try:
            # Try to make a simple API call to test connectivity
            test_result = self._perform_health_check()
            return {
                "source": self.source.value,
                "status": "healthy" if test_result else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "details": test_result,
            }
        except Exception as e:
            return {
                "source": self.source.value,
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    @abstractmethod
    def _perform_health_check(self) -> Any:
        """Perform adapter-specific health check.

        Returns:
            Health check result (implementation-specific)
        """
        pass


class AdapterError(Exception):
    """Base exception class for adapter-related errors."""

    def __init__(
        self,
        message: str,
        source: Optional[DataSource] = None,
        ticker: Optional[str] = None,
    ):
        """Initialize adapter error.

        Args:
            message: Error message
            source: Data source where error occurred
            ticker: Asset ticker related to the error
        """
        self.source = source
        self.ticker = ticker
        super().__init__(message)


class RateLimitError(AdapterError):
    """Exception raised when API rate limits are exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional error context
        """
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class DataNotAvailableError(AdapterError):
    """Exception raised when requested data is not available."""

    pass


class AuthenticationError(AdapterError):
    """Exception raised when API authentication fails."""

    pass


class InvalidTickerError(AdapterError):
    """Exception raised when ticker format is invalid or not supported."""

    pass
