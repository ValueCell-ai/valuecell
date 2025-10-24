"""Base classes and interfaces for asset data adapters.

This module defines the abstract base classes that all data source adapters
must implement to ensure consistent behavior across different providers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set

from .types import (
    Asset,
    AssetPrice,
    AssetSearchQuery,
    AssetSearchResult,
    AssetType,
    DataSource,
    Exchange,
)

logger = logging.getLogger(__name__)


@dataclass
class AdapterCapability:
    """Describes the asset types and exchanges supported by an adapter.

    This provides fine-grained control over adapter routing based on
    specific exchange and asset type combinations.
    """

    asset_type: AssetType
    exchanges: Set[Exchange]  # Supported exchanges

    def supports_exchange(self, exchange: Exchange) -> bool:
        """Check if this capability supports the given exchange."""
        return exchange in self.exchanges


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
            start_date: Start date for historical data, format: YYYY-MM-DD, timezone: UTC
            end_date: End date for historical data, format: YYYY-MM-DD, timezone: UTC
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
            ticker: Ticker in internal format (e.g., "NASDAQ:AAPL")

        Returns:
            True if ticker is valid for this adapter
        """
        try:
            if ":" not in ticker:
                return False

            exchange, _ = ticker.split(":", 1)
            capabilities = self.get_capabilities()

            # Check if any capability supports this exchange
            return any(
                cap.supports_exchange(Exchange(exchange)) for cap in capabilities
            )
        except Exception:
            return False

    @abstractmethod
    def convert_to_source_ticker(self, internal_ticker: str) -> str:
        """Convert internal ticker to data source format.

        Args:
            internal_ticker: Ticker in internal format (e.g., "NASDAQ:AAPL")
            source: Target data source

        Returns:
            Ticker in data source specific format (e.g., "AAPL" for yfinance)
        """
        pass

    @abstractmethod
    def convert_to_internal_ticker(
        self, source_ticker: str, default_exchange: Optional[str] = None
    ) -> str:
        """Convert data source ticker to internal format.
        Args:
            source_ticker: Ticker in data source format (e.g., "000001.SZ")
            source: Source data provider
            default_exchange: Default exchange if cannot be determined from ticker

        Returns:
            Ticker in internal format (e.g., "SZSE:000001")
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[AdapterCapability]:
        """Get detailed capabilities describing supported asset types and exchanges.

        Returns:
            List of capabilities describing what this adapter can handle
        """
        pass

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get list of asset types supported by this adapter.

        This method extracts asset types from capabilities.
        """
        capabilities = self.get_capabilities()
        asset_types = set()
        for cap in capabilities:
            asset_types.add(cap.asset_type)
        return list(asset_types)

    def get_supported_exchanges(self) -> Set[Exchange]:
        """Get set of all exchanges supported by this adapter.

        Returns:
            Set of Exchange enums
        """
        capabilities = self.get_capabilities()
        exchanges: Set[Exchange] = set()
        for cap in capabilities:
            exchanges.update(cap.exchanges)
        return exchanges
