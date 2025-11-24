"""Asset adapter manager for coordinating multiple data sources.

This module provides a unified interface for managing multiple data source adapters
and routing requests to the appropriate providers based on asset types and availability.
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

from valuecell.utils.model import get_model

from .akshare_adapter import AKShareAdapter
from .base import BaseDataAdapter
from .types import (
    Asset,
    AssetPrice,
    AssetSearchQuery,
    AssetSearchResult,
    AssetType,
    DataSource,
    Exchange,
    Watchlist,
)
from .yfinance_adapter import YFinanceAdapter

logger = logging.getLogger(__name__)


class AdapterManager:
    """Manager for coordinating multiple asset data adapters."""

    def __init__(self):
        """Initialize adapter manager."""
        self.adapters: Dict[DataSource, BaseDataAdapter] = {}

        # Exchange → Adapters routing table (simplified)
        # Note: Keys are Exchange.value strings for efficient lookup
        self.exchange_routing: Dict[str, List[BaseDataAdapter]] = {}

        # Ticker → Adapter cache for fast lookups
        self._ticker_cache: Dict[str, BaseDataAdapter] = {}
        self._cache_lock = threading.Lock()

        self.lock = threading.RLock()

        logger.info("Asset adapter manager initialized")

    def _rebuild_routing_table(self) -> None:
        """Rebuild routing table based on registered adapters' capabilities.

        Simplified: Only use exchange to determine adapter routing.
        """
        with self.lock:
            self.exchange_routing.clear()

            # Build routing table: Exchange → List[Adapters]
            for adapter in self.adapters.values():
                capabilities = adapter.get_capabilities()

                # Get all exchanges supported by this adapter (across all asset types)
                supported_exchanges = set()
                for cap in capabilities:
                    for exchange in cap.exchanges:
                        exchange_key = (
                            exchange.value
                            if isinstance(exchange, Exchange)
                            else exchange
                        )
                        supported_exchanges.add(exchange_key)

                # Register adapter for each supported exchange
                for exchange_key in supported_exchanges:
                    if exchange_key not in self.exchange_routing:
                        self.exchange_routing[exchange_key] = []
                    self.exchange_routing[exchange_key].append(adapter)

            # Clear ticker cache when routing table changes
            with self._cache_lock:
                self._ticker_cache.clear()

            logger.debug(
                f"Routing table rebuilt with {len(self.exchange_routing)} exchanges"
            )

    def register_adapter(self, adapter: BaseDataAdapter) -> None:
        """Register a data adapter and rebuild routing table.

        Args:
            adapter: Data adapter instance to register
        """
        with self.lock:
            self.adapters[adapter.source] = adapter
            self._rebuild_routing_table()
            logger.info(f"Registered adapter: {adapter.source.value}")

    def configure_yfinance(self, **kwargs) -> None:
        """Configure and register Yahoo Finance adapter."""
        try:
            adapter = YFinanceAdapter(**kwargs)
            self.register_adapter(adapter)
        except Exception as e:
            logger.error(f"Failed to configure Yahoo Finance adapter: {e}")

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

    def configure_baostock(self, **kwargs) -> None:
        """Configure and register BaoStock adapter.

        Args:
            **kwargs: Additional configuration
        """
        try:
            from .baostock_adapter import BaoStockAdapter

            adapter = BaoStockAdapter(**kwargs)
            self.register_adapter(adapter)
        except Exception as e:
            logger.error(f"Failed to configure BaoStock adapter: {e}")

    def get_available_adapters(self) -> List[DataSource]:
        """Get list of available data adapters."""
        with self.lock:
            return list(self.adapters.keys())

    def get_adapters_for_exchange(self, exchange: str) -> List[BaseDataAdapter]:
        """Get list of adapters for a specific exchange.

        Args:
            exchange: Exchange identifier (e.g., "NASDAQ", "SSE")

        Returns:
            List of adapters that support the exchange
        """
        with self.lock:
            return self.exchange_routing.get(exchange, [])

    def get_adapters_for_asset_type(
        self, asset_type: AssetType
    ) -> List[BaseDataAdapter]:
        """Get list of adapters that support a specific asset type.

        Note: This collects adapters across all exchanges. Consider using
        get_adapters_for_exchange() for more specific routing.

        Args:
            asset_type: Type of asset

        Returns:
            List of adapters that support this asset type
        """
        with self.lock:
            # Collect all adapters that support this asset type
            supporting_adapters = set()
            for adapter in self.adapters.values():
                supported_types = adapter.get_supported_asset_types()
                if asset_type in supported_types:
                    supporting_adapters.add(adapter)

            return list(supporting_adapters)

    def get_adapter_for_ticker(self, ticker: str) -> Optional[BaseDataAdapter]:
        """Get the best adapter for a specific ticker (with caching).

        Simplified: Only based on exchange, first adapter that validates wins.

        Args:
            ticker: Asset ticker in internal format (e.g., "NASDAQ:AAPL")

        Returns:
            Best available adapter for the ticker or None if not found
        """
        # Check cache first
        with self._cache_lock:
            if ticker in self._ticker_cache:
                return self._ticker_cache[ticker]

        # Parse ticker
        if ":" not in ticker:
            logger.warning(f"Invalid ticker format (missing ':'): {ticker}")
            return None

        exchange, symbol = ticker.split(":", 1)

        # Get adapters for this exchange
        adapters = self.get_adapters_for_exchange(exchange)

        if not adapters:
            logger.debug(f"No adapters registered for exchange: {exchange}")
            return None

        # Find first adapter that validates this ticker
        for adapter in adapters:
            if adapter.validate_ticker(ticker):
                # Cache the result
                with self._cache_lock:
                    self._ticker_cache[ticker] = adapter
                logger.debug(f"Matched adapter {adapter.source.value} for {ticker}")
                return adapter

        logger.warning(f"No suitable adapter found for ticker: {ticker}")
        return None

    def _deduplicate_search_results(
        self, results: List[AssetSearchResult]
    ) -> List[AssetSearchResult]:
        """Smart deduplication of search results to handle cross-exchange duplicates.

        This method handles cases where the same asset appears on multiple exchanges
        (e.g., AMEX:GORO vs NASDAQ:GORO). It prioritizes certain exchanges and removes
        likely duplicates based on symbol matching.

        Args:
            results: List of search results to deduplicate

        Returns:
            Deduplicated list of search results
        """
        # Exchange priority for US stocks (higher number = higher priority)
        exchange_priority = {
            "NASDAQ": 3,
            "NYSE": 2,
            "AMEX": 1,
            "HKEX": 3,
            "SSE": 2,
            "SZSE": 2,
            "BSE": 1,
        }

        seen_tickers = set()
        # Map: (symbol, country) -> best result so far
        symbol_map: Dict[tuple, AssetSearchResult] = {}
        unique_results = []

        for result in results:
            # Skip exact ticker duplicates
            if result.ticker in seen_tickers:
                continue

            try:
                exchange, symbol = result.ticker.split(":", 1)
            except ValueError:
                # Invalid ticker format, skip
                logger.warning(
                    f"Invalid ticker format in search result: {result.ticker}"
                )
                continue

            # Create a key for cross-exchange deduplication
            # Group by symbol and country to identify potential duplicates
            dedup_key = (symbol.upper(), result.country)

            # Check if we've seen this symbol in the same country before
            if dedup_key in symbol_map:
                existing_result = symbol_map[dedup_key]
                existing_exchange = existing_result.ticker.split(":")[0]

                # Compare exchange priorities
                current_priority = exchange_priority.get(exchange, 0)
                existing_priority = exchange_priority.get(existing_exchange, 0)

                if current_priority > existing_priority:
                    # Replace with higher priority exchange
                    symbol_map[dedup_key] = result
                    logger.debug(
                        f"Preferring {result.ticker} over {existing_result.ticker} (priority)"
                    )
                elif current_priority == existing_priority:
                    # Same priority, prefer the one with higher relevance score
                    if result.relevance_score > existing_result.relevance_score:
                        symbol_map[dedup_key] = result
                        logger.debug(
                            f"Preferring {result.ticker} over {existing_result.ticker} (relevance)"
                        )
                # else: keep existing result (lower priority exchange)
            else:
                # First time seeing this symbol, add it
                symbol_map[dedup_key] = result

            seen_tickers.add(result.ticker)

        # Convert map back to list
        unique_results = list(symbol_map.values())

        # Sort by relevance score (descending)
        unique_results.sort(key=lambda x: x.relevance_score, reverse=True)

        logger.info(
            f"Deduplicated {len(results)} results to {len(unique_results)} unique assets"
        )

        return unique_results

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
                    results = future.result(timeout=15)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(
                        f"Search failed for adapter {adapter.source.value}: {e}"
                    )

        # Smart deduplication of results
        unique_results = self._deduplicate_search_results(all_results)

        # Use fallback search if no results found
        if len(unique_results) == 0:
            logger.info(
                f"No results from adapters, trying fallback search for query: {query.query}"
            )
            fallback_results = self._fallback_search_assets(query)
            # Deduplicate fallback results with existing results
            combined_results = unique_results + fallback_results
            unique_results = self._deduplicate_search_results(combined_results)

        return unique_results[: query.limit]

    def _fallback_search_assets(
        self, query: AssetSearchQuery
    ) -> List[AssetSearchResult]:
        """Fallback search assets if no results are found using LLM-based ticker generation.

        This method uses the centralized configuration system to create model instances
        for intelligently generating possible ticker formats based on the user's search query,
        then validates each generated ticker.

        Args:
            query: Search query parameters

        Returns:
            List of validated search results
        """
        try:
            # Use configuration system to create model

            model = get_model("PRODUCT_MODEL_ID")

            # Create prompt to generate possible ticker formats
            system_prompt = (
                "You are a financial data expert that helps map search queries to "
                "standardized ticker formats. Always respond with valid JSON arrays only."
            )

            user_prompt = f"""Given the user search query: "{query.query}"

Generate a list of possible internal ticker IDs that match this query. The internal ticker format is: EXCHANGE:SYMBOL

Supported exchanges and their formats:
- NASDAQ: NASDAQ:SYMBOL (e.g., NASDAQ:AAPL, NASDAQ:MSFT)
- NYSE: NYSE:SYMBOL (e.g., NYSE:JPM, NYSE:BAC)
- AMEX: AMEX:SYMBOL (e.g., AMEX:GORO, AMEX:GLD)
- SSE: SSE:SYMBOL (Shanghai Stock Exchange, 6-digit code, e.g., SSE:601398, SSE:510050)
- SZSE: SZSE:SYMBOL (Shenzhen Stock Exchange, 6-digit code, e.g., SZSE:000001, SZSE:002594, SZSE:300750)
- BSE: BSE:SYMBOL (Beijing Stock Exchange, 6-digit code, e.g., BSE:835368, BSE:560800)
- HKEX: HKEX:SYMBOL (Hong Kong Stock Exchange, 5-digit code with leading zeros, e.g., HKEX:00700, HKEX:03033)
- CRYPTO: CRYPTO:SYMBOL (e.g., CRYPTO:BTC, CRYPTO:ETH)

Consider:
1. Common stock symbols and company names
2. Chinese company names (if query contains Chinese characters)
3. Cryptocurrency names
4. Index names
5. ETF names

Return ONLY a JSON array of ticker strings, like:
["NASDAQ:AAPL", "NYSE:AAPL", "HKEX:00700"]

Generate up to at least 1 possible ticker candidate up to 10. Be creative but realistic."""

            # Use agno Agent for structured communication
            from agno.agent import Agent

            agent = Agent(
                model=model,
                instructions=[system_prompt],
                markdown=False,
            )

            # Call LLM API
            response = agent.run(user_prompt)

            # Parse response
            response_text = response.content.strip()
            logger.debug(f"LLM response for query '{query.query}': {response_text}")

            # Extract JSON array from response (handle cases where LLM adds markdown formatting)
            if response_text.startswith("```json"):
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()

            possible_tickers = json.loads(response_text)

            if not isinstance(possible_tickers, list):
                logger.warning(f"LLM response is not a list: {possible_tickers}")
                return []

            # Validate each ticker and convert to search results
            results = []
            seen_tickers = set()

            for ticker in possible_tickers:
                if not isinstance(ticker, str):
                    continue

                ticker = ticker.strip().upper()

                # Skip duplicates
                if ticker in seen_tickers:
                    continue

                # Validate ticker format
                if ":" not in ticker:
                    continue

                if not self.get_adapter_for_ticker(ticker):
                    continue

                # Try to get asset info
                try:
                    asset_info = self.get_asset_info(ticker)

                    if asset_info:
                        seen_tickers.add(ticker)

                        # Convert Asset to AssetSearchResult
                        search_result = AssetSearchResult(
                            ticker=asset_info.ticker,
                            asset_type=asset_info.asset_type,
                            names=asset_info.names.names,
                            exchange=asset_info.market_info.exchange,
                            country=asset_info.market_info.country,
                        )
                        results.append(search_result)

                        logger.info(f"Fallback search found valid asset: {ticker}")

                        # Stop if we have enough results
                        if len(results) >= query.limit:
                            break

                except Exception as e:
                    logger.debug(f"Ticker {ticker} validation failed: {e}")
                    continue

            logger.info(
                f"Fallback search returned {len(results)} results for query '{query.query}'"
            )
            return results

        except Exception as e:
            logger.error(f"Fallback search failed: {e}", exc_info=True)
            return []

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed asset information with automatic failover.

        Args:
            ticker: Asset ticker in internal format

        Returns:
            Asset information or None if not found
        """
        # Get the primary adapter for this ticker
        adapter = self.get_adapter_for_ticker(ticker)

        if not adapter:
            logger.warning(f"No suitable adapter found for ticker: {ticker}")
            return None

        # Try the primary adapter
        try:
            logger.debug(
                f"Fetching asset info for {ticker} from {adapter.source.value}"
            )
            asset_info = adapter.get_asset_info(ticker)
            if asset_info:
                logger.info(
                    f"Successfully fetched asset info for {ticker} from {adapter.source.value}"
                )
                return asset_info
            else:
                logger.debug(
                    f"Adapter {adapter.source.value} returned None for {ticker}"
                )
        except Exception as e:
            logger.warning(
                f"Primary adapter {adapter.source.value} failed for {ticker}: {e}"
            )

        # Automatic failover: try other adapters for this exchange
        exchange = ticker.split(":")[0] if ":" in ticker else ""
        fallback_adapters = self.get_adapters_for_exchange(exchange)

        for fallback_adapter in fallback_adapters:
            # Skip the primary adapter we already tried
            if fallback_adapter.source == adapter.source:
                continue

            if not fallback_adapter.validate_ticker(ticker):
                continue

            try:
                logger.debug(
                    f"Fallback: trying {fallback_adapter.source.value} for {ticker}"
                )
                asset_info = fallback_adapter.get_asset_info(ticker)
                if asset_info:
                    logger.info(
                        f"Fallback success: fetched asset info for {ticker} from {fallback_adapter.source.value}"
                    )
                    # Update cache to use successful adapter
                    with self._cache_lock:
                        self._ticker_cache[ticker] = fallback_adapter
                    return asset_info
            except Exception as e:
                logger.warning(
                    f"Fallback adapter {fallback_adapter.source.value} failed for {ticker}: {e}"
                )
                continue

        logger.error(f"All adapters failed for {ticker}")
        return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price for an asset with automatic failover.

        Args:
            ticker: Asset ticker in internal format

        Returns:
            Current price data or None if not available
        """
        # Get the primary adapter for this ticker
        adapter = self.get_adapter_for_ticker(ticker)

        if not adapter:
            logger.warning(f"No suitable adapter found for ticker: {ticker}")
            return None

        # Try the primary adapter
        try:
            logger.debug(f"Fetching price for {ticker} from {adapter.source.value}")
            price = adapter.get_real_time_price(ticker)
            if price:
                logger.info(
                    f"Successfully fetched price for {ticker} from {adapter.source.value}"
                )
                return price
            else:
                logger.debug(
                    f"Adapter {adapter.source.value} returned None for {ticker}"
                )
        except Exception as e:
            logger.warning(
                f"Primary adapter {adapter.source.value} failed for {ticker}: {e}"
            )

        # Automatic failover: try other adapters for this exchange
        exchange = ticker.split(":")[0] if ":" in ticker else ""
        fallback_adapters = self.get_adapters_for_exchange(exchange)

        for fallback_adapter in fallback_adapters:
            # Skip the primary adapter we already tried
            if fallback_adapter.source == adapter.source:
                continue

            if not fallback_adapter.validate_ticker(ticker):
                continue

            try:
                logger.debug(
                    f"Fallback: trying {fallback_adapter.source.value} for {ticker}"
                )
                price = fallback_adapter.get_real_time_price(ticker)
                if price:
                    logger.info(
                        f"Fallback success: fetched price for {ticker} from {fallback_adapter.source.value}"
                    )
                    # Update cache to use successful adapter
                    with self._cache_lock:
                        self._ticker_cache[ticker] = fallback_adapter
                    return price
            except Exception as e:
                logger.warning(
                    f"Fallback adapter {fallback_adapter.source.value} failed for {ticker}: {e}"
                )
                continue

        logger.error(f"All adapters failed for {ticker}")
        return None

    def get_multiple_prices(
        self, tickers: List[str]
    ) -> Dict[str, Optional[AssetPrice]]:
        """Get real-time prices for multiple assets efficiently with automatic failover.

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
        failed_tickers = []

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
                    # Separate successful and failed results
                    for ticker, price in results.items():
                        if price is not None:
                            all_results[ticker] = price
                        else:
                            failed_tickers.append(ticker)
                except Exception as e:
                    logger.warning(
                        f"Batch price fetch failed for adapter {adapter.source.value}: {e}"
                    )
                    # Mark all tickers from this adapter as failed
                    failed_tickers.extend(adapter_tickers[adapter])

        # Retry failed tickers individually with fallback adapters
        if failed_tickers:
            logger.info(
                f"Retrying {len(failed_tickers)} failed tickers with fallback adapters"
            )
            for ticker in failed_tickers:
                if ticker not in all_results or all_results[ticker] is None:
                    # Try to get price with automatic failover
                    price = self.get_real_time_price(ticker)
                    all_results[ticker] = price

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
        """Get historical price data for an asset with automatic failover.

        Args:
            ticker: Asset ticker in internal format
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval

        Returns:
            List of historical price data
        """
        # Get the primary adapter for this ticker
        adapter = self.get_adapter_for_ticker(ticker)

        if not adapter:
            logger.warning(f"No suitable adapter found for ticker: {ticker}")
            return []

        # Try the primary adapter
        try:
            logger.debug(
                f"Fetching historical data for {ticker} from {adapter.source.value}"
            )
            prices = adapter.get_historical_prices(
                ticker, start_date, end_date, interval
            )
            if prices:
                logger.info(
                    f"Successfully fetched {len(prices)} historical prices for {ticker} from {adapter.source.value}"
                )
                return prices
            else:
                logger.debug(
                    f"Adapter {adapter.source.value} returned empty historical data for {ticker}"
                )
        except Exception as e:
            logger.warning(
                f"Primary adapter {adapter.source.value} failed for historical data of {ticker}: {e}"
            )

        # Automatic failover: try other adapters for this exchange
        exchange = ticker.split(":")[0] if ":" in ticker else ""
        fallback_adapters = self.get_adapters_for_exchange(exchange)

        for fallback_adapter in fallback_adapters:
            # Skip the primary adapter we already tried
            if fallback_adapter.source == adapter.source:
                continue

            if not fallback_adapter.validate_ticker(ticker):
                continue

            try:
                logger.debug(
                    f"Fallback: trying {fallback_adapter.source.value} for historical data of {ticker}"
                )
                prices = fallback_adapter.get_historical_prices(
                    ticker, start_date, end_date, interval
                )
                if prices:
                    logger.info(
                        f"Fallback success: fetched {len(prices)} historical prices for {ticker} from {fallback_adapter.source.value}"
                    )
                    # Update cache to use successful adapter
                    with self._cache_lock:
                        self._ticker_cache[ticker] = fallback_adapter
                    return prices
            except Exception as e:
                logger.warning(
                    f"Fallback adapter {fallback_adapter.source.value} failed for historical data of {ticker}: {e}"
                )
                continue

        logger.error(f"All adapters failed for historical data of {ticker}")
        return []


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
