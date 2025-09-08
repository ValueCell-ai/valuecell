"""Asset adapter manager for coordinating multiple data sources.

This module provides a unified interface for managing multiple data source adapters
and routing requests to the appropriate providers based on asset types and availability.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .base import BaseDataAdapter
from .types import (
    Asset,
    AssetPrice,
    AssetSearchResult,
    AssetSearchQuery,
    DataSource,
    AssetType,
    Watchlist,
)
from .yfinance_adapter import YFinanceAdapter
from .tushare_adapter import TuShareAdapter
from .coinmarketcap_adapter import CoinMarketCapAdapter
from .akshare_adapter import AKShareAdapter
from .finnhub_adapter import FinnhubAdapter

logger = logging.getLogger(__name__)


class AdapterManager:
    """Manager for coordinating multiple asset data adapters."""

    def __init__(self):
        """Initialize adapter manager."""
        self.adapters: Dict[DataSource, BaseDataAdapter] = {}
        self.adapter_priorities: Dict[AssetType, List[DataSource]] = {}
        self.lock = threading.RLock()

        # Default adapter priorities by asset type
        self._set_default_priorities()

        logger.info("Asset adapter manager initialized")

    def _set_default_priorities(self) -> None:
        """Set default adapter priorities for different asset types."""
        self.adapter_priorities = {
            AssetType.STOCK: [
                DataSource.YFINANCE,
                DataSource.FINNHUB,
                DataSource.TUSHARE,
                DataSource.AKSHARE,
            ],
            AssetType.ETF: [
                DataSource.YFINANCE,
                DataSource.FINNHUB,
                DataSource.AKSHARE,
            ],
            AssetType.CRYPTO: [
                DataSource.COINMARKETCAP,
                DataSource.YFINANCE,
                DataSource.AKSHARE,
            ],
            AssetType.INDEX: [
                DataSource.YFINANCE,
                DataSource.TUSHARE,
                DataSource.AKSHARE,
            ],
        }

    def register_adapter(self, adapter: BaseDataAdapter) -> None:
        """Register a data adapter.

        Args:
            adapter: Data adapter instance to register
        """
        with self.lock:
            self.adapters[adapter.source] = adapter
            logger.info(f"Registered adapter: {adapter.source.value}")

    def unregister_adapter(self, source: DataSource) -> None:
        """Unregister a data adapter.

        Args:
            source: Data source to unregister
        """
        with self.lock:
            if source in self.adapters:
                del self.adapters[source]
                logger.info(f"Unregistered adapter: {source.value}")

    def configure_yfinance(self, **kwargs) -> None:
        """Configure and register Yahoo Finance adapter."""
        try:
            adapter = YFinanceAdapter(**kwargs)
            self.register_adapter(adapter)
        except Exception as e:
            logger.error(f"Failed to configure Yahoo Finance adapter: {e}")

    def configure_tushare(self, api_key: str, **kwargs) -> None:
        """Configure and register TuShare adapter.

        Args:
            api_key: TuShare API key
            **kwargs: Additional configuration
        """
        try:
            adapter = TuShareAdapter(api_key=api_key, **kwargs)
            self.register_adapter(adapter)
        except Exception as e:
            logger.error(f"Failed to configure TuShare adapter: {e}")

    def configure_coinmarketcap(self, api_key: str, **kwargs) -> None:
        """Configure and register CoinMarketCap adapter.

        Args:
            api_key: CoinMarketCap API key
            **kwargs: Additional configuration
        """
        try:
            adapter = CoinMarketCapAdapter(api_key=api_key, **kwargs)
            self.register_adapter(adapter)
        except Exception as e:
            logger.error(f"Failed to configure CoinMarketCap adapter: {e}")

    def configure_akshare(self, **kwargs) -> None:
        """Configure and register AKShare adapter.

        Args:
            **kwargs: Additional configuration
        """
        try:
            adapter = AKShareAdapter(**kwargs)
            self.register_adapter(adapter)
        except Exception as e:
            logger.error(f"Failed to configure AKShare adapter: {e}")

    def configure_finnhub(self, api_key: str, **kwargs) -> None:
        """Configure and register Finnhub adapter.

        Args:
            api_key: Finnhub API key
            **kwargs: Additional configuration
        """
        try:
            adapter = FinnhubAdapter(api_key=api_key, **kwargs)
            self.register_adapter(adapter)
        except Exception as e:
            logger.error(f"Failed to configure Finnhub adapter: {e}")

    def get_available_adapters(self) -> List[DataSource]:
        """Get list of available data adapters."""
        with self.lock:
            return list(self.adapters.keys())

    def get_adapters_for_asset_type(
        self, asset_type: AssetType
    ) -> List[BaseDataAdapter]:
        """Get prioritized list of adapters for an asset type.

        Args:
            asset_type: Type of asset

        Returns:
            List of adapters in priority order
        """
        with self.lock:
            priority_sources = self.adapter_priorities.get(asset_type, [])
            adapters = []

            for source in priority_sources:
                if source in self.adapters:
                    adapters.append(self.adapters[source])

            return adapters

    def get_adapter_for_ticker(self, ticker: str) -> Optional[BaseDataAdapter]:
        """Get the best adapter for a specific ticker.

        Args:
            ticker: Asset ticker in internal format

        Returns:
            Best available adapter for the ticker
        """
        with self.lock:
            # Try to determine asset type from ticker
            exchange = ticker.split(":")[0] if ":" in ticker else ""

            # Map exchanges to likely asset types
            exchange_asset_mapping = {
                "NASDAQ": AssetType.STOCK,
                "NYSE": AssetType.STOCK,
                "SSE": AssetType.STOCK,
                "SZSE": AssetType.STOCK,
                "HKEX": AssetType.STOCK,
                "CRYPTO": AssetType.CRYPTO,
            }

            asset_type = exchange_asset_mapping.get(exchange, AssetType.STOCK)
            adapters = self.get_adapters_for_asset_type(asset_type)

            # Return first adapter that supports this ticker
            for adapter in adapters:
                if adapter.validate_ticker(ticker):
                    return adapter

            return None

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets across all available adapters.

        Args:
            query: Search query parameters

        Returns:
            Combined and deduplicated search results
        """
        all_results = []

        # Determine which adapters to use based on asset types
        target_adapters = set()

        if query.asset_types:
            for asset_type in query.asset_types:
                target_adapters.update(self.get_adapters_for_asset_type(asset_type))
        else:
            # Use all available adapters
            with self.lock:
                target_adapters.update(self.adapters.values())

        # Search in parallel across adapters
        if not target_adapters:
            return []

        with ThreadPoolExecutor(max_workers=len(target_adapters)) as executor:
            future_to_adapter = {
                executor.submit(adapter.search_assets, query): adapter
                for adapter in target_adapters
            }

            for future in as_completed(future_to_adapter):
                adapter = future_to_adapter[future]
                try:
                    results = future.result(timeout=30)  # 30 second timeout
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(
                        f"Search failed for adapter {adapter.source.value}: {e}"
                    )

        # Deduplicate results by ticker
        seen_tickers = set()
        unique_results = []

        # Sort by relevance score first
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)

        for result in all_results:
            if result.ticker not in seen_tickers:
                seen_tickers.add(result.ticker)
                unique_results.append(result)

        return unique_results[: query.limit]

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed asset information.

        Args:
            ticker: Asset ticker in internal format

        Returns:
            Asset information or None if not found
        """
        adapter = self.get_adapter_for_ticker(ticker)
        if not adapter:
            logger.warning(f"No suitable adapter found for ticker: {ticker}")
            return None

        try:
            return adapter.get_asset_info(ticker)
        except Exception as e:
            logger.error(f"Error fetching asset info for {ticker}: {e}")
            return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price for an asset.

        Args:
            ticker: Asset ticker in internal format

        Returns:
            Current price data or None if not available
        """
        adapter = self.get_adapter_for_ticker(ticker)
        if not adapter:
            logger.warning(f"No suitable adapter found for ticker: {ticker}")
            return None

        try:
            return adapter.get_real_time_price(ticker)
        except Exception as e:
            logger.error(f"Error fetching real-time price for {ticker}: {e}")
            return None

    def get_multiple_prices(
        self, tickers: List[str]
    ) -> Dict[str, Optional[AssetPrice]]:
        """Get real-time prices for multiple assets efficiently.

        Args:
            tickers: List of asset tickers

        Returns:
            Dictionary mapping tickers to price data
        """
        # Group tickers by adapter
        adapter_tickers: Dict[BaseDataAdapter, List[str]] = {}

        for ticker in tickers:
            adapter = self.get_adapter_for_ticker(ticker)
            if adapter:
                if adapter not in adapter_tickers:
                    adapter_tickers[adapter] = []
                adapter_tickers[adapter].append(ticker)

        # Fetch prices in parallel from each adapter
        all_results = {}

        if not adapter_tickers:
            # If no adapters found for any tickers, return None for all
            return {ticker: None for ticker in tickers}

        with ThreadPoolExecutor(max_workers=len(adapter_tickers)) as executor:
            future_to_adapter = {
                executor.submit(adapter.get_multiple_prices, ticker_list): adapter
                for adapter, ticker_list in adapter_tickers.items()
            }

            for future in as_completed(future_to_adapter):
                adapter = future_to_adapter[future]
                try:
                    results = future.result(timeout=60)  # 60 second timeout
                    all_results.update(results)
                except Exception as e:
                    logger.warning(
                        f"Batch price fetch failed for adapter {adapter.source.value}: {e}"
                    )

        # Ensure all requested tickers are in results
        for ticker in tickers:
            if ticker not in all_results:
                all_results[ticker] = None

        return all_results

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
            interval: Data interval

        Returns:
            List of historical price data
        """
        adapter = self.get_adapter_for_ticker(ticker)
        if not adapter:
            logger.warning(f"No suitable adapter found for ticker: {ticker}")
            return []

        try:
            return adapter.get_historical_prices(ticker, start_date, end_date, interval)
        except Exception as e:
            logger.error(f"Error fetching historical prices for {ticker}: {e}")
            return []

    def health_check(self) -> Dict[DataSource, Dict[str, Any]]:
        """Perform health check on all registered adapters.

        Returns:
            Dictionary mapping data sources to health status
        """
        health_results = {}

        # If no adapters are registered, return empty results
        if not self.adapters:
            return health_results

        with ThreadPoolExecutor(max_workers=len(self.adapters)) as executor:
            future_to_source = {
                executor.submit(adapter.health_check): source
                for source, adapter in self.adapters.items()
            }

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    result = future.result(timeout=30)
                    health_results[source] = result
                except Exception as e:
                    health_results[source] = {
                        "status": "error",
                        "message": f"Health check failed: {e}",
                        "timestamp": datetime.utcnow().isoformat(),
                    }

        return health_results

    def get_supported_asset_types(self) -> Dict[DataSource, List[AssetType]]:
        """Get supported asset types for each adapter.

        Returns:
            Dictionary mapping data sources to supported asset types
        """
        supported_types = {}

        with self.lock:
            for source, adapter in self.adapters.items():
                try:
                    supported_types[source] = adapter.get_supported_asset_types()
                except Exception as e:
                    logger.warning(
                        f"Error getting supported types for {source.value}: {e}"
                    )
                    supported_types[source] = []

        return supported_types

    def set_adapter_priority(
        self, asset_type: AssetType, sources: List[DataSource]
    ) -> None:
        """Set adapter priority for an asset type.

        Args:
            asset_type: Asset type to configure
            sources: List of data sources in priority order
        """
        with self.lock:
            self.adapter_priorities[asset_type] = sources
            logger.info(
                f"Updated adapter priority for {asset_type.value}: {[s.value for s in sources]}"
            )


class WatchlistManager:
    """Manager for user watchlists and portfolio tracking."""

    def __init__(self, adapter_manager: AdapterManager):
        """Initialize watchlist manager.

        Args:
            adapter_manager: Asset adapter manager instance
        """
        self.adapter_manager = adapter_manager
        self.watchlists: Dict[
            str, Dict[str, Watchlist]
        ] = {}  # user_id -> watchlist_name -> Watchlist
        self.lock = threading.RLock()

        logger.info("Watchlist manager initialized")

    def create_watchlist(
        self,
        user_id: str,
        name: str = "My Watchlist",
        description: str = "",
        is_default: bool = False,
    ) -> Watchlist:
        """Create a new watchlist for a user.

        Args:
            user_id: User identifier
            name: Watchlist name
            description: Watchlist description
            is_default: Whether this is the default watchlist

        Returns:
            Created watchlist
        """
        with self.lock:
            if user_id not in self.watchlists:
                self.watchlists[user_id] = {}

            # If this is the first watchlist, make it default
            if not self.watchlists[user_id]:
                is_default = True

            # If setting as default, unset other defaults
            if is_default:
                for watchlist in self.watchlists[user_id].values():
                    watchlist.is_default = False

            watchlist = Watchlist(
                user_id=user_id,
                name=name,
                description=description,
                is_default=is_default,
            )

            self.watchlists[user_id][name] = watchlist
            logger.info(f"Created watchlist '{name}' for user {user_id}")

            return watchlist

    def get_watchlist(self, user_id: str, name: str) -> Optional[Watchlist]:
        """Get a specific watchlist.

        Args:
            user_id: User identifier
            name: Watchlist name

        Returns:
            Watchlist or None if not found
        """
        with self.lock:
            return self.watchlists.get(user_id, {}).get(name)

    def get_default_watchlist(self, user_id: str) -> Optional[Watchlist]:
        """Get user's default watchlist.

        Args:
            user_id: User identifier

        Returns:
            Default watchlist or None if not found
        """
        with self.lock:
            user_watchlists = self.watchlists.get(user_id, {})

            for watchlist in user_watchlists.values():
                if watchlist.is_default:
                    return watchlist

            # If no default found but user has watchlists, return first one
            if user_watchlists:
                return list(user_watchlists.values())[0]

            return None

    def get_user_watchlists(self, user_id: str) -> List[Watchlist]:
        """Get all watchlists for a user.

        Args:
            user_id: User identifier

        Returns:
            List of user's watchlists
        """
        with self.lock:
            return list(self.watchlists.get(user_id, {}).values())

    def add_asset_to_watchlist(
        self,
        user_id: str,
        ticker: str,
        watchlist_name: Optional[str] = None,
        notes: str = "",
    ) -> bool:
        """Add an asset to a watchlist.

        Args:
            user_id: User identifier
            ticker: Asset ticker to add
            watchlist_name: Watchlist name (uses default if None)
            notes: User notes about the asset

        Returns:
            True if added successfully, False otherwise
        """
        with self.lock:
            # Get watchlist
            if watchlist_name:
                watchlist = self.get_watchlist(user_id, watchlist_name)
            else:
                watchlist = self.get_default_watchlist(user_id)

                # Create default watchlist if none exists
                if not watchlist:
                    watchlist = self.create_watchlist(user_id, is_default=True)

            if not watchlist:
                logger.error(f"Could not find or create watchlist for user {user_id}")
                return False

            # Validate ticker exists
            asset_info = self.adapter_manager.get_asset_info(ticker)
            if not asset_info:
                logger.warning(f"Asset not found: {ticker}")
                return False

            # Add to watchlist
            watchlist.add_asset(ticker, notes)
            logger.info(
                f"Added {ticker} to watchlist '{watchlist.name}' for user {user_id}"
            )

            return True

    def remove_asset_from_watchlist(
        self, user_id: str, ticker: str, watchlist_name: Optional[str] = None
    ) -> bool:
        """Remove an asset from a watchlist.

        Args:
            user_id: User identifier
            ticker: Asset ticker to remove
            watchlist_name: Watchlist name (uses default if None)

        Returns:
            True if removed successfully, False otherwise
        """
        with self.lock:
            # Get watchlist
            if watchlist_name:
                watchlist = self.get_watchlist(user_id, watchlist_name)
            else:
                watchlist = self.get_default_watchlist(user_id)

            if not watchlist:
                return False

            success = watchlist.remove_asset(ticker)
            if success:
                logger.info(
                    f"Removed {ticker} from watchlist '{watchlist.name}' for user {user_id}"
                )

            return success

    def get_watchlist_prices(
        self, user_id: str, watchlist_name: Optional[str] = None
    ) -> Dict[str, Optional[AssetPrice]]:
        """Get current prices for all assets in a watchlist.

        Args:
            user_id: User identifier
            watchlist_name: Watchlist name (uses default if None)

        Returns:
            Dictionary mapping tickers to price data
        """
        # Get watchlist
        if watchlist_name:
            watchlist = self.get_watchlist(user_id, watchlist_name)
        else:
            watchlist = self.get_default_watchlist(user_id)

        if not watchlist:
            return {}

        tickers = watchlist.get_tickers()
        if not tickers:
            return {}

        return self.adapter_manager.get_multiple_prices(tickers)

    def delete_watchlist(self, user_id: str, name: str) -> bool:
        """Delete a watchlist.

        Args:
            user_id: User identifier
            name: Watchlist name to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        with self.lock:
            if user_id not in self.watchlists:
                return False

            if name not in self.watchlists[user_id]:
                return False

            del self.watchlists[user_id][name]
            logger.info(f"Deleted watchlist '{name}' for user {user_id}")

            return True


# Global instances
_adapter_manager: Optional[AdapterManager] = None
_watchlist_manager: Optional[WatchlistManager] = None


def get_adapter_manager() -> AdapterManager:
    """Get global adapter manager instance."""
    global _adapter_manager
    if _adapter_manager is None:
        _adapter_manager = AdapterManager()
    return _adapter_manager


def get_watchlist_manager() -> WatchlistManager:
    """Get global watchlist manager instance."""
    global _watchlist_manager
    if _watchlist_manager is None:
        _watchlist_manager = WatchlistManager(get_adapter_manager())
    return _watchlist_manager


def reset_managers() -> None:
    """Reset global manager instances (mainly for testing)."""
    global _adapter_manager, _watchlist_manager
    _adapter_manager = None
    _watchlist_manager = None
