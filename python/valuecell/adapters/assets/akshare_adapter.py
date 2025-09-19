"""AKShare adapter for Chinese user-friendly financial market data.

This adapter provides integration with AKShare library to fetch comprehensive
Global financial market data including stocks, funds, bonds, and economic indicators.
"""

import logging
from typing import List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import decimal
import pandas as pd
import time
import threading

try:
    import akshare as ak
except ImportError:
    ak = None

from .base import BaseDataAdapter
from .types import (
    Asset,
    AssetPrice,
    AssetSearchResult,
    AssetSearchQuery,
    DataSource,
    AssetType,
    MarketInfo,
    LocalizedName,
    MarketStatus,
)

logger = logging.getLogger(__name__)


class AKShareAdapter(BaseDataAdapter):
    """AKShare data adapter for Chinese financial markets."""

    def __init__(self, **kwargs):
        """Initialize AKShare adapter.

        Args:
            **kwargs: Additional configuration parameters
        """
        super().__init__(DataSource.AKSHARE, **kwargs)

        if ak is None:
            raise ImportError(
                "akshare library is required. Install with: pip install akshare"
            )

    def _initialize(self) -> None:
        """Initialize AKShare adapter configuration."""
        self.timeout = self.config.get("timeout", 10)  # Reduced timeout duration

        # Different cache TTLs for different data types
        self.price_cache_ttl = self.config.get(
            "price_cache_ttl", 30
        )  # 30 seconds for real-time prices
        self.info_cache_ttl = self.config.get(
            "info_cache_ttl", 3600
        )  # 1 hour for stock info
        self.hist_cache_ttl = self.config.get(
            "hist_cache_ttl", 1800
        )  # 30 minutes for historical data

        self.max_retries = self.config.get("max_retries", 2)  # Maximum retry attempts

        # Data caching with different TTLs
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._last_cache_clear = time.time()

        # Cache statistics for monitoring
        self._cache_stats = {"hits": 0, "misses": 0, "evictions": 0}

        # Asset type mapping for AKShare
        self.asset_type_mapping = {
            "stock": AssetType.STOCK,
            "fund": AssetType.ETF,
            # "bond": AssetType.BOND,
            "index": AssetType.INDEX,
        }

        # Field mapping - Handle AKShare API field changes
        self.field_mappings = {
            "a_shares": {
                "code": ["代码", "symbol", "ts_code"],
                "name": ["名称", "name", "short_name"],
                "price": ["最新价", "close", "price"],
                "open": ["今开", "open"],
                "high": ["最高", "high"],
                "low": ["最低", "low"],
                "volume": ["成交量", "volume", "vol"],
                "market_cap": ["总市值", "total_mv"],
            },
            "hk_stocks": {
                "code": ["symbol", "code", "代码"],
                "name": ["name", "名称", "short_name"],
            },
            "us_stocks": {
                "code": ["代码", "symbol", "ticker"],
                "name": ["名称", "name", "short_name"],
            },
        }

        # Exchange mapping for AKShare
        self.exchange_mapping = {
            "SH": "SSE",  # Shanghai Stock Exchange
            "SZ": "SZSE",  # Shenzhen Stock Exchange
            "BJ": "BSE",  # Beijing Stock Exchange
            "HK": "HKEX",  # Hong Kong Stock Exchange
            "US": "NASDAQ",  # US markets (generic)
            "NYSE": "NYSE",  # New York Stock Exchange
            "NASDAQ": "NASDAQ",  # NASDAQ
        }

        logger.info("AKShare adapter initialized with caching and field mapping")

    def _get_cached_data(self, cache_key: str, fetch_func, *args, **kwargs):
        """Get cached data or fetch new data with adaptive TTL."""
        current_time = time.time()

        # Determine TTL based on cache key type
        ttl = self._get_cache_ttl(cache_key)

        with self._cache_lock:
            # Clean up expired cache periodically
            if current_time - self._last_cache_clear > min(
                self.price_cache_ttl, self.info_cache_ttl
            ):
                expired_keys = [
                    key
                    for key, (_, timestamp, key_ttl) in self._cache.items()
                    if current_time - timestamp
                    > key_ttl * 2  # Keep expired data for fallback
                ]
                for key in expired_keys:
                    del self._cache[key]
                    self._cache_stats["evictions"] += 1
                self._last_cache_clear = current_time

            # Check for valid cache
            if cache_key in self._cache:
                cached_data, timestamp, key_ttl = self._cache[cache_key]
                if current_time - timestamp < key_ttl:
                    logger.debug(f"Cache hit for {cache_key}")
                    self._cache_stats["hits"] += 1
                    return cached_data
                else:
                    logger.debug(f"Cache expired for {cache_key}")

        # Cache miss
        self._cache_stats["misses"] += 1

        # Fetch new data outside the lock to reduce lock time
        try:
            logger.debug(f"Fetching new data for {cache_key}")
            data = fetch_func(*args, **kwargs)
            with self._cache_lock:
                self._cache[cache_key] = (data, current_time, ttl)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch data for {cache_key}: {e}")
            # Try to return expired data as fallback
            with self._cache_lock:
                if cache_key in self._cache:
                    cached_data, _, _ = self._cache[cache_key]
                    logger.warning(f"Using expired cached data for {cache_key}")
                    return cached_data
            raise

    def _get_cache_ttl(self, cache_key: str) -> int:
        """Get appropriate TTL based on cache key type."""
        if "price" in cache_key or "spot" in cache_key:
            return self.price_cache_ttl
        elif "hist" in cache_key:
            return self.hist_cache_ttl
        else:
            return self.info_cache_ttl

    def get_cache_stats(self) -> dict:
        """Get cache statistics for monitoring."""
        with self._cache_lock:
            total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
            hit_rate = (
                self._cache_stats["hits"] / total_requests if total_requests > 0 else 0
            )
            return {
                "cache_size": len(self._cache),
                "hit_rate": hit_rate,
                **self._cache_stats,
            }

    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self._cache_lock:
            self._cache.clear()
            self._cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
            logger.info("Cache cleared")

    def _safe_get_field(self, data_row, field_type: str, market_type: str = "a_shares"):
        """Safely get data field value, handling field name changes."""
        possible_fields = self.field_mappings.get(market_type, {}).get(field_type, [])

        for field_name in possible_fields:
            if field_name in data_row and data_row[field_name] is not None:
                return data_row[field_name]

        logger.debug(f"Field {field_type} not found in {market_type} data")
        return None

    def _safe_akshare_call(self, func, *args, **kwargs):
        """Safely call AKShare API with retry mechanism."""
        for attempt in range(self.max_retries + 1):
            try:
                # Set timeout
                result = func(*args, **kwargs)
                if result is not None and not (
                    hasattr(result, "empty") and result.empty
                ):
                    return result
                else:
                    logger.warning(
                        f"AKShare API returned empty data on attempt {attempt + 1}"
                    )
                    if attempt < self.max_retries:
                        time.sleep(1)  # Wait 1 second before retry
                        continue
                    return None
            except Exception as e:
                logger.warning(f"AKShare API call failed on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
                raise e
        return None

    def _get_exchange_from_a_share_code(self, stock_code: str) -> Optional[tuple]:
        """Get exchange and ticker from A-share stock code."""
        if stock_code.startswith("6"):
            return ("SSE", f"SSE:{stock_code}")
        elif stock_code.startswith(("0", "3")):
            return ("SZSE", f"SZSE:{stock_code}")
        elif stock_code.startswith("8"):
            return ("BSE", f"BSE:{stock_code}")
        return None

    def _create_stock_search_result(
        self,
        ticker: str,
        asset_type: AssetType,
        stock_code: str,
        stock_name: str,
        exchange: str,
        country: str,
        currency: str,
        search_term: str,
    ) -> AssetSearchResult:
        """Create a standardized stock search result."""
        names = {
            "zh-Hans": stock_name,
            "zh-Hant": stock_name,
            "en-US": stock_name,
        }

        return AssetSearchResult(
            ticker=ticker,
            asset_type=asset_type,
            names=names,
            exchange=exchange,
            country=country,
            currency=currency,
            market_status=MarketStatus.UNKNOWN,
            relevance_score=self._calculate_relevance(
                search_term, stock_code, stock_name
            ),
        )

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets using AKShare direct queries."""
        try:
            results = []
            search_term = query.query.strip()

            # Direct ticker lookup strategy - try to match exact codes first
            if self._looks_like_ticker(search_term):
                results.extend(self._search_by_direct_ticker_lookup(search_term, query))
                if results:
                    return results[: query.limit]

            # Determine likely markets based on search term
            likely_markets = self._determine_likely_markets(search_term, query)

            # Search markets by priority using direct queries
            if "a_shares" in likely_markets:
                results.extend(self._search_a_shares_direct(search_term, query))

            if "hk_stocks" in likely_markets and len(results) < query.limit:
                results.extend(self._search_hk_stocks_direct(search_term, query))

            if "us_stocks" in likely_markets and len(results) < query.limit:
                results.extend(self._search_us_stocks_direct(search_term, query))

            if "etfs" in likely_markets and len(results) < query.limit:
                results.extend(self._search_etfs_direct(search_term, query))

            # Apply filters
            if query.asset_types:
                results = [r for r in results if r.asset_type in query.asset_types]

            if query.exchanges:
                results = [r for r in results if r.exchange in query.exchanges]

            if query.countries:
                results = [r for r in results if r.country in query.countries]

            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)

            return results[: query.limit]

        except Exception as e:
            logger.error(f"Error searching assets: {e}")
            return []

    def _determine_likely_markets(
        self, search_term: str, query: AssetSearchQuery
    ) -> List[str]:
        """Intelligently determine likely markets for search term, reducing unnecessary network requests."""
        likely_markets = set()  # Use set to avoid duplicates
        search_term_upper = search_term.upper().strip()

        # Mappings for efficient lookup
        exchange_market_map = {
            "SSE": "a_shares",
            "SZSE": "a_shares",
            "BSE": "a_shares",
            "HKEX": "hk_stocks",
            "NASDAQ": "us_stocks",
            "NYSE": "us_stocks",
            "CRYPTO": "crypto",
        }

        country_market_map = {
            "CN": ["a_shares", "etfs"],
            "HK": ["hk_stocks"],
            "US": ["us_stocks"],
            "GLOBAL": ["crypto"],
        }

        # Determine markets based on query filters
        if query.asset_types:
            type_market_map = {
                AssetType.ETF: "etfs",
                AssetType.STOCK: ["a_shares", "hk_stocks", "us_stocks"],
            }
            for asset_type in query.asset_types:
                markets = type_market_map.get(asset_type, [])
                if isinstance(markets, str):
                    likely_markets.add(markets)
                else:
                    likely_markets.update(markets)

        if query.exchanges:
            for exchange in query.exchanges:
                market = exchange_market_map.get(exchange)
                if market:
                    likely_markets.add(market)

        if query.countries:
            for country in query.countries:
                markets = country_market_map.get(country, [])
                likely_markets.update(markets)

        # If no explicit filters, determine based on search term patterns
        if not likely_markets:
            likely_markets.update(self._analyze_search_term_pattern(search_term_upper))

        # If still empty, search all markets
        if not likely_markets:
            likely_markets = {"a_shares", "us_stocks", "hk_stocks", "etfs"}

        # Convert to list with priority order
        priority_order = ["a_shares", "us_stocks", "hk_stocks", "etfs"]
        result = [market for market in priority_order if market in likely_markets]

        logger.debug(f"Determined likely markets for '{search_term}': {result}")
        return result

    def _analyze_search_term_pattern(self, search_term_upper: str) -> set:
        """Analyze search term pattern to determine likely markets."""
        markets = set()

        # A-share code pattern (6 digits starting with specific numbers)
        if (
            search_term_upper.isdigit()
            and len(search_term_upper) == 6
            and search_term_upper.startswith(("6", "0", "3", "8"))
        ):
            markets.add("a_shares")

        # HK stock code pattern
        elif (
            search_term_upper.isdigit() and 1 <= len(search_term_upper) <= 5
        ) or search_term_upper.startswith("00"):
            markets.add("hk_stocks")

        # US stock/crypto pattern (letters)
        elif search_term_upper.isalpha() and len(search_term_upper) <= 5:
            markets.add("us_stocks")

        # Chinese names - prioritize A-shares
        elif any("\u4e00" <= char <= "\u9fff" for char in search_term_upper):
            markets.update(["a_shares", "hk_stocks"])

        # Default case
        else:
            markets.update(["a_shares", "us_stocks", "hk_stocks", "etfs"])

        return markets

    def _search_a_shares_direct(
        self, search_term: str, query: AssetSearchQuery
    ) -> List[AssetSearchResult]:
        """Search A-share stocks using direct queries."""
        results = []

        # If search term looks like A-share code, try direct lookup
        if self._is_a_share_code(search_term):
            result = self._get_a_share_by_code(search_term)
            if result:
                results.append(result)
                return results

        # For name searches, try fuzzy matching with common patterns
        # This is a simplified approach - in production, you might want to use
        # a search service or maintain a local index
        if len(search_term) >= 2:  # Only search if term is meaningful
            # Try some common A-share codes that might match the search term
            candidate_codes = self._generate_a_share_candidates(search_term)

            for code in candidate_codes[: query.limit]:
                try:
                    result = self._get_a_share_by_code(code)
                    if result and self._matches_search_term(result, search_term):
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Failed to get A-share info for {code}: {e}")
                    continue

        return results

    def _is_a_share_code(self, search_term: str) -> bool:
        """Check if search term looks like an A-share code."""
        return (
            search_term.isdigit()
            and len(search_term) == 6
            and search_term.startswith(("6", "0", "3", "8"))
        )

    def _get_a_share_by_code(self, stock_code: str) -> Optional[AssetSearchResult]:
        """Get A-share info by stock code using direct query."""
        try:
            # Use individual stock info query
            cache_key = f"a_share_info_{stock_code}"
            df_info = self._get_cached_data(
                cache_key,
                self._safe_akshare_call,
                ak.stock_individual_info_em,
                symbol=stock_code,
            )

            if df_info is None or df_info.empty:
                return None

            # Extract stock name from info
            info_dict = {}
            for _, row in df_info.iterrows():
                info_dict[row["item"]] = row["value"]

            stock_name = info_dict.get("股票名称", stock_code)

            # Determine exchange from code
            exchange_info = self._get_exchange_from_a_share_code(stock_code)
            if not exchange_info:
                return None

            exchange, internal_ticker = exchange_info

            return self._create_stock_search_result(
                internal_ticker,
                AssetType.STOCK,
                stock_code,
                stock_name,
                exchange,
                "CN",
                "CNY",
                stock_code,
            )

        except Exception as e:
            logger.debug(f"Error getting A-share info for {stock_code}: {e}")
            return None

    def _generate_a_share_candidates(self, search_term: str) -> List[str]:
        """Generate candidate A-share codes based on search term."""
        candidates = []

        # If it's a partial number, try to complete it
        if search_term.isdigit() and len(search_term) < 6:
            # Try common prefixes
            for prefix in ["6", "0", "3"]:
                if search_term.startswith(prefix) or not search_term.startswith(
                    ("6", "0", "3", "8")
                ):
                    padded = search_term.ljust(6, "0")
                    if not search_term.startswith(("6", "0", "3", "8")):
                        candidates.extend(
                            [f"{prefix}{padded[1:]}" for prefix in ["6", "0", "3"]]
                        )
                    else:
                        candidates.append(padded)

        # For Chinese names, we would need a mapping service
        # For now, return some common stocks as examples
        common_stocks = [
            "000001",  # 平安银行
            "000002",  # 万科A
            "600000",  # 浦发银行
            "600036",  # 招商银行
            "600519",  # 贵州茅台
        ]

        if not candidates and any("\u4e00" <= char <= "\u9fff" for char in search_term):
            candidates.extend(common_stocks)

        return candidates[:10]  # Limit candidates

    def _matches_search_term(self, result: AssetSearchResult, search_term: str) -> bool:
        """Check if search result matches the search term."""
        search_lower = search_term.lower()

        # Check ticker
        if search_lower in result.ticker.lower():
            return True

        # Check names
        for name in result.names.values():
            if name and search_lower in name.lower():
                return True

        return False

    def _search_hk_stocks_direct(
        self, search_term: str, query: AssetSearchQuery
    ) -> List[AssetSearchResult]:
        """Search Hong Kong stocks using direct queries."""
        results = []

        # If search term looks like HK stock code, try direct lookup
        if self._is_hk_stock_code(search_term):
            result = self._get_hk_stock_by_code(search_term)
            if result:
                results.append(result)
                return results

        # For other searches, try common HK stock codes
        candidate_codes = self._generate_hk_stock_candidates(search_term)

        for code in candidate_codes[: query.limit]:
            try:
                result = self._get_hk_stock_by_code(code)
                if result and self._matches_search_term(result, search_term):
                    results.append(result)
            except Exception as e:
                logger.debug(f"Failed to get HK stock info for {code}: {e}")
                continue

        return results

    def _is_hk_stock_code(self, search_term: str) -> bool:
        """Check if search term looks like a HK stock code."""
        return search_term.isdigit() and 1 <= len(search_term) <= 5

    def _get_hk_stock_by_code(self, stock_code: str) -> Optional[AssetSearchResult]:
        """Get HK stock info by stock code using direct query."""
        try:
            # Format HK stock code
            formatted_code = (
                stock_code.zfill(5) if not stock_code.startswith("0") else stock_code
            )

            # Try to get HK stock data - note: AKShare may not have direct individual HK stock query
            # so we create a basic result based on code
            internal_ticker = f"HKEX:{formatted_code}"

            # Create basic result - in production, you might want to query actual HK stock info
            return self._create_stock_search_result(
                internal_ticker,
                AssetType.STOCK,
                formatted_code,
                f"HK{formatted_code}",  # Basic name
                "HKEX",
                "HK",
                "HKD",
                stock_code,
            )

        except Exception as e:
            logger.debug(f"Error getting HK stock info for {stock_code}: {e}")
            return None

    def _generate_hk_stock_candidates(self, search_term: str) -> List[str]:
        """Generate candidate HK stock codes based on search term."""
        candidates = []

        # Common HK stocks
        common_hk_stocks = [
            "00700",  # 腾讯
            "00941",  # 中国移动
            "01299",  # 友邦保险
            "02318",  # 中国平安
            "03988",  # 中国银行
        ]

        if search_term.isdigit() and len(search_term) <= 5:
            candidates.append(search_term.zfill(5))
        else:
            candidates.extend(common_hk_stocks)

        return candidates[:10]

    def _search_us_stocks_direct(
        self, search_term: str, query: AssetSearchQuery
    ) -> List[AssetSearchResult]:
        """Search US stocks using direct queries."""
        results = []

        # If search term looks like US stock symbol, try direct lookup
        if self._is_us_stock_symbol(search_term):
            result = self._get_us_stock_by_symbol(search_term)
            if result:
                results.append(result)
                return results

        # For other searches, try common US stock symbols
        candidate_symbols = self._generate_us_stock_candidates(search_term)

        for symbol in candidate_symbols[: query.limit]:
            try:
                result = self._get_us_stock_by_symbol(symbol)
                if result and self._matches_search_term(result, search_term):
                    results.append(result)
            except Exception as e:
                logger.debug(f"Failed to get US stock info for {symbol}: {e}")
                continue

        return results

    def _is_us_stock_symbol(self, search_term: str) -> bool:
        """Check if search term looks like a US stock symbol."""
        return search_term.isalpha() and 1 <= len(search_term) <= 5

    def _get_us_stock_by_symbol(self, symbol: str) -> Optional[AssetSearchResult]:
        """Get US stock info by symbol using direct query."""
        try:
            # Create basic result - AKShare may not have direct individual US stock query
            exchange = "NASDAQ"  # Default to NASDAQ
            internal_ticker = f"{exchange}:{symbol.upper()}"

            return self._create_stock_search_result(
                internal_ticker,
                AssetType.STOCK,
                symbol.upper(),
                symbol.upper(),  # Basic name
                exchange,
                "US",
                "USD",
                symbol,
            )

        except Exception as e:
            logger.debug(f"Error getting US stock info for {symbol}: {e}")
            return None

    def _generate_us_stock_candidates(self, search_term: str) -> List[str]:
        """Generate candidate US stock symbols based on search term."""
        candidates = []

        # Common US stocks
        common_us_stocks = [
            "AAPL",  # Apple
            "GOOGL",  # Google
            "MSFT",  # Microsoft
            "AMZN",  # Amazon
            "TSLA",  # Tesla
        ]

        if search_term.isalpha() and len(search_term) <= 5:
            candidates.append(search_term.upper())
        else:
            candidates.extend(common_us_stocks)

        return candidates[:10]

    def _search_etfs_direct(
        self, search_term: str, query: AssetSearchQuery
    ) -> List[AssetSearchResult]:
        """Search ETFs using direct queries."""
        results = []

        # If search term looks like ETF code, try direct lookup
        if self._is_etf_code(search_term):
            result = self._get_etf_by_code(search_term)
            if result:
                results.append(result)
                return results

        # For other searches, try common ETF codes
        candidate_codes = self._generate_etf_candidates(search_term)

        for code in candidate_codes[: query.limit]:
            try:
                result = self._get_etf_by_code(code)
                if result and self._matches_search_term(result, search_term):
                    results.append(result)
            except Exception as e:
                logger.debug(f"Failed to get ETF info for {code}: {e}")
                continue

        return results

    def _is_etf_code(self, search_term: str) -> bool:
        """Check if search term looks like an ETF code."""
        return (
            search_term.isdigit()
            and len(search_term) == 6
            and search_term.startswith(("5", "1"))
        )

    def _get_etf_by_code(self, fund_code: str) -> Optional[AssetSearchResult]:
        """Get ETF info by code using direct query."""
        try:
            # Determine exchange for funds
            exchange = "SSE" if fund_code.startswith("5") else "SZSE"
            internal_ticker = f"{exchange}:{fund_code}"

            # Create basic result - in production, you might want to query actual ETF info
            names = {
                "zh-Hans": f"ETF{fund_code}",
                "zh-Hant": f"ETF{fund_code}",
                "en-US": f"ETF{fund_code}",
            }

            return AssetSearchResult(
                ticker=internal_ticker,
                asset_type=AssetType.ETF,
                names=names,
                exchange=exchange,
                country="CN",
                currency="CNY",
                market_status=MarketStatus.UNKNOWN,
                relevance_score=2.0,  # High relevance for direct matches
            )

        except Exception as e:
            logger.debug(f"Error getting ETF info for {fund_code}: {e}")
            return None

    def _generate_etf_candidates(self, search_term: str) -> List[str]:
        """Generate candidate ETF codes based on search term."""
        candidates = []

        # Common ETFs
        common_etfs = [
            "510050",  # 50ETF
            "510300",  # 沪深300ETF
            "159919",  # 沪深300ETF
            "510500",  # 中证500ETF
            "159915",  # 创业板ETF
        ]

        if search_term.isdigit() and len(search_term) == 6:
            candidates.append(search_term)
        else:
            candidates.extend(common_etfs)

        return candidates[:10]

    def _calculate_relevance(self, search_term: str, code: str, name: str) -> float:
        """Calculate relevance score for search results."""
        search_term_lower = search_term.lower()
        code_lower = code.lower()
        name_lower = name.lower()

        # Exact matches get highest score
        if search_term_lower == code_lower or search_term_lower == name_lower:
            return 2.0

        # Code starts with search term
        if code_lower.startswith(search_term_lower):
            return 1.8

        # Name starts with search term
        if name_lower.startswith(search_term_lower):
            return 1.6

        # Code contains search term
        if search_term_lower in code_lower:
            return 1.4

        # Name contains search term
        if search_term_lower in name_lower:
            return 1.2

        return 1.0

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed asset information from AKShare."""
        try:
            exchange, symbol = ticker.split(":")

            # Handle different markets
            if exchange in ["SSE", "SZSE", "BSE"]:
                return self._get_a_share_info(ticker, exchange, symbol)
            elif exchange == "HKEX":
                return self._get_hk_stock_info(ticker, exchange, symbol)
            elif exchange in ["NASDAQ", "NYSE"]:
                return self._get_us_stock_info(ticker, exchange, symbol)
            else:
                logger.warning(f"Unsupported exchange: {exchange}")
                return None

        except Exception as e:
            logger.error(f"Error getting asset info for {ticker}: {e}")
            return None

    def _get_a_share_info(
        self, ticker: str, exchange: str, symbol: str
    ) -> Optional[Asset]:
        """Get A-share stock information."""
        try:
            # Use the new Snowball API for individual stock basic info
            df_info = ak.stock_individual_basic_info_xq(symbol=symbol)

            if df_info is None or df_info.empty:
                return None

            # Convert DataFrame to dict for easier access
            info_dict = {}
            for _, row in df_info.iterrows():
                info_dict[row["item"]] = row["value"]

            # Create localized names
            names = LocalizedName()
            stock_name_cn = info_dict.get("org_short_name_cn", symbol)
            stock_name_en = info_dict.get("org_short_name_en", symbol)
            names.set_name("zh-Hans", stock_name_cn)
            names.set_name("zh-Hant", stock_name_cn)
            names.set_name("en-US", stock_name_en)

            # Create market info
            market_info = MarketInfo(
                exchange=exchange,
                country="CN",
                currency="CNY",
                timezone="Asia/Shanghai",
            )

            # Create asset
            asset = Asset(
                ticker=ticker,
                asset_type=AssetType.STOCK,
                names=names,
                market_info=market_info,
            )

            # Set source mapping
            asset.set_source_ticker(self.source, symbol)

            # Add additional properties from Snowball API
            properties = {
                "org_id": info_dict.get("org_id"),
                "org_name_cn": info_dict.get("org_name_cn"),
                "org_short_name_cn": info_dict.get("org_short_name_cn"),
                "org_name_en": info_dict.get("org_name_en"),
                "org_short_name_en": info_dict.get("org_short_name_en"),
                "main_operation_business": info_dict.get("main_operation_business"),
                "operating_scope": info_dict.get("operating_scope"),
                "org_cn_introduction": info_dict.get("org_cn_introduction"),
                "legal_representative": info_dict.get("legal_representative"),
                "general_manager": info_dict.get("general_manager"),
                "secretary": info_dict.get("secretary"),
                "established_date": info_dict.get("established_date"),
                "reg_asset": info_dict.get("reg_asset"),
                "staff_num": info_dict.get("staff_num"),
                "telephone": info_dict.get("telephone"),
                "postcode": info_dict.get("postcode"),
                "fax": info_dict.get("fax"),
                "email": info_dict.get("email"),
                "org_website": info_dict.get("org_website"),
                "reg_address_cn": info_dict.get("reg_address_cn"),
                "reg_address_en": info_dict.get("reg_address_en"),
                "office_address_cn": info_dict.get("office_address_cn"),
                "office_address_en": info_dict.get("office_address_en"),
                "currency": info_dict.get("currency"),
                "listed_date": info_dict.get("listed_date"),
                "provincial_name": info_dict.get("provincial_name"),
                "actual_controller": info_dict.get("actual_controller"),
                "classi_name": info_dict.get("classi_name"),
                "pre_name_cn": info_dict.get("pre_name_cn"),
                "chairman": info_dict.get("chairman"),
                "executives_nums": info_dict.get("executives_nums"),
                "actual_issue_vol": info_dict.get("actual_issue_vol"),
                "issue_price": info_dict.get("issue_price"),
                "actual_rc_net_amt": info_dict.get("actual_rc_net_amt"),
                "pe_after_issuing": info_dict.get("pe_after_issuing"),
                "online_success_rate_of_issue": info_dict.get(
                    "online_success_rate_of_issue"
                ),
                "affiliate_industry": info_dict.get("affiliate_industry"),
            }

            # Filter out None values
            properties = {k: v for k, v in properties.items() if v is not None}
            asset.properties.update(properties)

            return asset

        except Exception as e:
            logger.error(f"Error fetching A-share info for {symbol}: {e}")
            return None

    def _get_hk_stock_info(
        self, ticker: str, exchange: str, symbol: str
    ) -> Optional[Asset]:
        """Get Hong Kong stock information."""
        try:
            # For HK stocks, we'll create basic info since detailed info API may be limited
            names = LocalizedName()
            names.set_name("zh-Hans", symbol)
            names.set_name("zh-Hant", symbol)
            names.set_name("en-US", symbol)

            market_info = MarketInfo(
                exchange=exchange,
                country="HK",
                currency="HKD",
                timezone="Asia/Hong_Kong",
            )

            asset = Asset(
                ticker=ticker,
                asset_type=AssetType.STOCK,
                names=names,
                market_info=market_info,
            )

            asset.set_source_ticker(self.source, symbol)
            return asset

        except Exception as e:
            logger.error(f"Error creating HK stock info for {symbol}: {e}")
            return None

    def _get_us_stock_info(
        self, ticker: str, exchange: str, symbol: str
    ) -> Optional[Asset]:
        """Get US stock information."""
        try:
            # For US stocks, we'll create basic info since detailed info API may be limited
            names = LocalizedName()
            names.set_name("zh-Hans", symbol)
            names.set_name("zh-Hant", symbol)
            names.set_name("en-US", symbol)

            market_info = MarketInfo(
                exchange=exchange,
                country="US",
                currency="USD",
                timezone="America/New_York",
            )

            asset = Asset(
                ticker=ticker,
                asset_type=AssetType.STOCK,
                names=names,
                market_info=market_info,
            )

            asset.set_source_ticker(self.source, symbol)
            return asset

        except Exception as e:
            logger.error(f"Error creating US stock info for {symbol}: {e}")
            return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data from AKShare."""
        try:
            exchange, symbol = ticker.split(":")

            # Handle different markets
            if exchange in ["SSE", "SZSE", "BSE"]:
                return self._get_a_share_price(ticker, exchange, symbol)
            elif exchange == "HKEX":
                return self._get_hk_stock_price(ticker, exchange, symbol)
            elif exchange in ["NASDAQ", "NYSE"]:
                return self._get_us_stock_price(ticker, exchange, symbol)
            else:
                logger.warning(f"Unsupported exchange for real-time price: {exchange}")
                return None

        except Exception as e:
            logger.error(f"Error getting real-time price for {ticker}: {e}")
            return None

    def _get_a_share_price(
        self, ticker: str, exchange: str, symbol: str
    ) -> Optional[AssetPrice]:
        """Get A-share real-time price using direct query."""
        try:
            # Use direct real-time price query - stock_zh_a_spot_em takes no parameters
            cache_key = "a_share_price_all"
            df_realtime = self._get_cached_data(
                cache_key, self._safe_akshare_call, ak.stock_zh_a_spot_em
            )

            if df_realtime is None or df_realtime.empty:
                # Fallback to individual stock info if spot price fails
                return self._get_a_share_price_from_info(ticker, exchange, symbol)

            # Find the specific stock in the A-share data
            # The dataframe contains all A-shares, we need to filter by stock code
            stock_data = df_realtime[df_realtime["代码"] == symbol]
            if stock_data.empty:
                # If not found by exact match, try alternative matching
                logger.warning(
                    f"Stock {symbol} not found in A-share spot data, falling back to individual info"
                )
                return self._get_a_share_price_from_info(ticker, exchange, symbol)

            stock_info = stock_data.iloc[0]

            # Extract price information using safe field access
            current_price = self._safe_decimal_convert(stock_info.get("最新价", 0))
            open_price = self._safe_decimal_convert(stock_info.get("今开", 0))
            high_price = self._safe_decimal_convert(stock_info.get("最高", 0))
            low_price = self._safe_decimal_convert(stock_info.get("最低", 0))
            pre_close = self._safe_decimal_convert(stock_info.get("昨收", 0))

            # Calculate change
            change = current_price - pre_close if current_price and pre_close else None
            change_percent = (
                (change / pre_close) * 100
                if change and pre_close and pre_close != 0
                else None
            )

            # Get volume and market cap
            volume = self._safe_decimal_convert(stock_info.get("成交量"))
            market_cap = self._safe_decimal_convert(stock_info.get("总市值"))

            return AssetPrice(
                ticker=ticker,
                price=current_price,
                currency="CNY",
                timestamp=datetime.now(),
                volume=volume,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=current_price,
                change=change,
                change_percent=change_percent,
                market_cap=market_cap,
                source=self.source,
            )

        except Exception as e:
            logger.error(f"Error fetching A-share price for {symbol}: {e}")
            return None

    def _get_a_share_price_from_info(
        self, ticker: str, exchange: str, symbol: str
    ) -> Optional[AssetPrice]:
        """Get A-share price from individual stock info as fallback."""
        try:
            # Try to get basic price info from stock individual info
            cache_key = f"a_share_info_price_{symbol}"
            df_info = self._get_cached_data(
                cache_key,
                self._safe_akshare_call,
                ak.stock_individual_info_em,
                symbol=symbol,
            )

            if df_info is None or df_info.empty:
                logger.warning(f"No individual stock info available for {symbol}")
                return None

            # Convert DataFrame to dict for easier access
            info_dict = {}
            for _, row in df_info.iterrows():
                info_dict[row["item"]] = row["value"]

            # Extract current price from the individual info (if available)
            current_price_value = info_dict.get("最新", info_dict.get("现价", 0))
            current_price = self._safe_decimal_convert(current_price_value)

            # Get market cap and other info
            market_cap = self._safe_decimal_convert(info_dict.get("总市值"))

            if not current_price or current_price == 0:
                logger.warning(
                    f"No valid current price found for {symbol} in individual info"
                )
                return None

            return AssetPrice(
                ticker=ticker,
                price=current_price,
                currency="CNY",
                timestamp=datetime.now(),
                volume=None,  # Not available in individual info
                open_price=None,  # Not available in individual info
                high_price=None,  # Not available in individual info
                low_price=None,  # Not available in individual info
                close_price=current_price,
                change=None,  # Not available in individual info
                change_percent=None,  # Not available in individual info
                market_cap=market_cap,
                source=self.source,
            )

        except Exception as e:
            logger.error(f"Error fetching A-share info price for {symbol}: {e}")
            return None

    def _safe_decimal_convert(self, value) -> Optional[Decimal]:
        """Safely convert value to Decimal."""
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, decimal.InvalidOperation):
            return None

    def _get_hk_stock_price(
        self, ticker: str, exchange: str, symbol: str
    ) -> Optional[AssetPrice]:
        """Get Hong Kong stock real-time price using individual stock query."""
        try:
            # Use individual stock query instead of downloading all HK stocks
            # Try to get individual stock info first
            try:
                # For HK stocks, try to get historical data as a proxy for current price
                df_hk_hist = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
                if df_hk_hist is not None and not df_hk_hist.empty:
                    latest = df_hk_hist.iloc[-1]
                    current_price = Decimal(
                        str(latest.get("close", latest.get("收盘", 0)))
                    )

                    return AssetPrice(
                        ticker=ticker,
                        price=current_price,
                        currency="HKD",
                        timestamp=datetime.now(),
                        volume=Decimal(
                            str(latest.get("volume", latest.get("成交量", 0)))
                        )
                        if latest.get("volume", latest.get("成交量", 0))
                        else None,
                        open_price=Decimal(
                            str(latest.get("open", latest.get("开盘", 0)))
                        ),
                        high_price=Decimal(
                            str(latest.get("high", latest.get("最高", 0)))
                        ),
                        low_price=Decimal(
                            str(latest.get("low", latest.get("最低", 0)))
                        ),
                        close_price=current_price,
                        change=None,
                        change_percent=None,
                        market_cap=None,
                        source=self.source,
                    )
            except Exception as e:
                logger.debug(f"Individual HK stock query failed for {symbol}: {e}")

            # Fallback: return None instead of downloading all HK stocks
            logger.warning(
                f"Unable to get HK stock price for {symbol} without full market data download"
            )
            return None

        except Exception as e:
            logger.error(f"Error fetching HK stock price for {symbol}: {e}")
            return None

    def _get_us_stock_price(
        self, ticker: str, exchange: str, symbol: str
    ) -> Optional[AssetPrice]:
        """Get US stock real-time price using individual stock query."""
        try:
            # Use individual stock query instead of downloading all US stocks
            try:
                # For US stocks, try to get historical data as a proxy for current price
                df_us_hist = ak.stock_us_daily(symbol=symbol, adjust="qfq")
                if df_us_hist is not None and not df_us_hist.empty:
                    latest = df_us_hist.iloc[-1]
                    current_price = Decimal(
                        str(latest.get("close", latest.get("收盘", 0)))
                    )

                    return AssetPrice(
                        ticker=ticker,
                        price=current_price,
                        currency="USD",
                        timestamp=datetime.now(),
                        volume=Decimal(
                            str(latest.get("volume", latest.get("成交量", 0)))
                        )
                        if latest.get("volume", latest.get("成交量", 0))
                        else None,
                        open_price=Decimal(
                            str(latest.get("open", latest.get("开盘", 0)))
                        ),
                        high_price=Decimal(
                            str(latest.get("high", latest.get("最高", 0)))
                        ),
                        low_price=Decimal(
                            str(latest.get("low", latest.get("最低", 0)))
                        ),
                        close_price=current_price,
                        change=None,
                        change_percent=None,
                        market_cap=None,
                        source=self.source,
                    )
            except Exception as e:
                logger.debug(f"Individual US stock query failed for {symbol}: {e}")

            # Fallback: return None instead of downloading all US stocks
            logger.warning(
                f"Unable to get US stock price for {symbol} without full market data download"
            )
            return None

        except Exception as e:
            logger.error(f"Error fetching US stock price for {symbol}: {e}")
            return None

    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[AssetPrice]:
        """Get historical price data from AKShare."""
        try:
            exchange, symbol = ticker.split(":")

            # Handle different markets
            if exchange in ["SSE", "SZSE", "BSE"]:
                return self._get_a_share_historical(
                    ticker, exchange, symbol, start_date, end_date, interval
                )
            elif exchange == "HKEX":
                return self._get_hk_stock_historical(
                    ticker, exchange, symbol, start_date, end_date, interval
                )
            elif exchange in ["NASDAQ", "NYSE"]:
                return self._get_us_stock_historical(
                    ticker, exchange, symbol, start_date, end_date, interval
                )
            else:
                logger.warning(f"Unsupported exchange for historical data: {exchange}")
                return []

        except Exception as e:
            logger.error(f"Error getting historical prices for {ticker}: {e}")
            return []

    def _get_a_share_historical(
        self,
        ticker: str,
        exchange: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str,
    ) -> List[AssetPrice]:
        """Get A-share historical price data using direct query."""
        try:
            # Format dates for AKShare
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")

            # Map interval to AKShare format
            if interval in ["1d", "daily"]:
                period = "daily"
            else:
                logger.warning(
                    f"AKShare primarily supports daily data. Requested interval: {interval}"
                )
                period = "daily"

            # Use cached data for historical prices
            cache_key = (
                f"a_share_hist_{symbol}_{start_date_str}_{end_date_str}_{period}"
            )
            df_hist = self._get_cached_data(
                cache_key,
                self._safe_akshare_call,
                ak.stock_zh_a_hist,
                symbol=symbol,
                period=period,
                start_date=start_date_str,
                end_date=end_date_str,
                adjust="",  # No adjustment
            )

            if df_hist is None or df_hist.empty:
                logger.warning(f"No historical data available for {symbol}")
                return []

            prices = []
            for _, row in df_hist.iterrows():
                try:
                    # Parse date safely
                    trade_date = pd.to_datetime(row["日期"]).to_pydatetime()

                    # Extract price data safely
                    open_price = self._safe_decimal_convert(row.get("开盘"))
                    high_price = self._safe_decimal_convert(row.get("最高"))
                    low_price = self._safe_decimal_convert(row.get("最低"))
                    close_price = self._safe_decimal_convert(row.get("收盘"))
                    volume = self._safe_decimal_convert(row.get("成交量"))

                    if not close_price:  # Skip if no closing price
                        continue

                    # Calculate change from previous day
                    change = None
                    change_percent = None
                    if len(prices) > 0:
                        prev_close = prices[-1].close_price
                        if prev_close and prev_close != 0:
                            change = close_price - prev_close
                            change_percent = (change / prev_close) * 100

                    price = AssetPrice(
                        ticker=ticker,
                        price=close_price,
                        currency="CNY",
                        timestamp=trade_date,
                        volume=volume,
                        open_price=open_price,
                        high_price=high_price,
                        low_price=low_price,
                        close_price=close_price,
                        change=change,
                        change_percent=change_percent,
                        source=self.source,
                    )
                    prices.append(price)

                except Exception as row_error:
                    logger.warning(
                        f"Error processing historical data row for {symbol}: {row_error}"
                    )
                    continue

            logger.info(f"Retrieved {len(prices)} historical price points for {symbol}")
            return prices

        except Exception as e:
            logger.error(f"Error fetching A-share historical data for {symbol}: {e}")
            return []

    def _get_hk_stock_historical(
        self,
        ticker: str,
        exchange: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str,
    ) -> List[AssetPrice]:
        """Get Hong Kong stock historical price data."""
        try:
            # Use AKShare HK stock historical data
            df_hist = ak.stock_hk_daily(symbol=symbol, adjust="qfq")

            if df_hist is None or df_hist.empty:
                return []

            # Filter by date range
            df_hist["date"] = pd.to_datetime(df_hist["date"])
            mask = (df_hist["date"] >= start_date) & (df_hist["date"] <= end_date)
            df_hist = df_hist[mask]

            prices = []
            for _, row in df_hist.iterrows():
                trade_date = row["date"].to_pydatetime()

                # Extract price data (adjust field names based on actual data structure)
                open_price = Decimal(str(row.get("open", 0)))
                high_price = Decimal(str(row.get("high", 0)))
                low_price = Decimal(str(row.get("low", 0)))
                close_price = Decimal(str(row.get("close", 0)))
                volume = (
                    Decimal(str(row.get("volume", 0))) if row.get("volume") else None
                )

                price = AssetPrice(
                    ticker=ticker,
                    price=close_price,
                    currency="HKD",
                    timestamp=trade_date,
                    volume=volume,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    change=None,
                    change_percent=None,
                    source=self.source,
                )
                prices.append(price)

            return prices

        except Exception as e:
            logger.error(f"Error fetching HK stock historical data for {symbol}: {e}")
            return []

    def _get_us_stock_historical(
        self,
        ticker: str,
        exchange: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str,
    ) -> List[AssetPrice]:
        """Get US stock historical price data."""
        try:
            # Use AKShare US stock historical data
            df_hist = ak.stock_us_daily(symbol=symbol, adjust="qfq")

            if df_hist is None or df_hist.empty:
                return []

            # Filter by date range
            df_hist["date"] = pd.to_datetime(df_hist["date"])
            mask = (df_hist["date"] >= start_date) & (df_hist["date"] <= end_date)
            df_hist = df_hist[mask]

            prices = []
            for _, row in df_hist.iterrows():
                trade_date = row["date"].to_pydatetime()

                # Extract price data
                open_price = Decimal(str(row.get("open", 0)))
                high_price = Decimal(str(row.get("high", 0)))
                low_price = Decimal(str(row.get("low", 0)))
                close_price = Decimal(str(row.get("close", 0)))
                volume = (
                    Decimal(str(row.get("volume", 0))) if row.get("volume") else None
                )

                price = AssetPrice(
                    ticker=ticker,
                    price=close_price,
                    currency="USD",
                    timestamp=trade_date,
                    volume=volume,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    change=None,
                    change_percent=None,
                    source=self.source,
                )
                prices.append(price)

            return prices

        except Exception as e:
            logger.error(f"Error fetching US stock historical data for {symbol}: {e}")
            return []

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get asset types supported by AKShare."""
        return [
            AssetType.STOCK,
            AssetType.ETF,
            AssetType.INDEX,
        ]

    def _perform_health_check(self) -> Any:
        """Perform health check by testing a simple stock info call instead of full data download."""
        try:
            # Test with a simple individual stock info call instead of downloading all market data
            # This avoids the expensive full market data download during health checks
            try:
                # Test A-share with a known stock (Ping An Bank)
                df_test = ak.stock_individual_info_em(symbol="000001")
                if df_test is not None and not df_test.empty:
                    return {
                        "status": "ok",
                        "test_method": "individual_stock_info",
                        "test_symbol": "000001",
                        "response_received": True,
                    }
            except Exception as e:
                logger.debug(f"A-share test failed: {e}")

            # Fallback: just check if akshare module is available and importable
            import akshare as ak_test

            if ak_test:
                return {
                    "status": "ok",
                    "test_method": "module_import",
                    "message": "AKShare module available",
                }
            else:
                return {"status": "error", "message": "AKShare module not available"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _looks_like_ticker(self, search_term: str) -> bool:
        """Check if search term looks like a ticker symbol."""
        search_term = search_term.upper().strip()

        # Combined heuristics for ticker-like patterns
        return (len(search_term) <= 6 and search_term.isalnum()) or (
            len(search_term) <= 10 and search_term.isalpha()
        )

    def _search_by_direct_ticker_lookup(
        self, search_term: str, query: AssetSearchQuery
    ) -> List[AssetSearchResult]:
        """Search by direct ticker lookup as fallback for semantic search.

        This method provides a yfinance-like approach for cases where AKShare
        doesn't have comprehensive search capabilities.
        """
        search_term = search_term.upper().strip()

        # Generate ticker variations based on search term characteristics
        ticker_variations = self._generate_ticker_variations(search_term)

        for ticker_format in ticker_variations:
            try:
                # Try to get asset info to validate the ticker
                asset_info = self.get_asset_info(ticker_format)
                if asset_info:
                    # Create search result from asset info
                    result = AssetSearchResult(
                        ticker=ticker_format,
                        asset_type=asset_info.asset_type,
                        names={
                            "zh-Hans": asset_info.names.get_name("zh-Hans")
                            or search_term,
                            "zh-Hant": asset_info.names.get_name("zh-Hant")
                            or search_term,
                            "en-US": asset_info.names.get_name("en-US") or search_term,
                        },
                        exchange=asset_info.market_info.exchange,
                        country=asset_info.market_info.country,
                        currency=asset_info.market_info.currency,
                        market_status=MarketStatus.UNKNOWN,
                        relevance_score=2.0,  # High relevance for direct matches
                    )
                    return [result]  # Return immediately on first match

            except Exception as e:
                logger.debug(f"Ticker lookup failed for {ticker_format}: {e}")
                continue

        return []

    def _generate_ticker_variations(self, search_term: str) -> List[str]:
        """Generate ticker variations based on search term characteristics."""
        variations = [search_term]  # Direct ticker first

        # A-share variations (6 digits)
        if search_term.isdigit() and len(search_term) == 6:
            if search_term.startswith("6"):
                variations.append(f"SSE:{search_term}")
            elif search_term.startswith(("0", "3")):
                variations.append(f"SZSE:{search_term}")
            elif search_term.startswith("8"):
                variations.append(f"BSE:{search_term}")

        # HK variations (digits, potentially short)
        elif search_term.isdigit() and 1 <= len(search_term) <= 5:
            variations.extend(
                [
                    f"HKEX:{search_term}",
                    f"HKEX:{search_term.zfill(5)}",  # Pad with zeros
                ]
            )

        # US/Crypto variations (letters)
        elif search_term.isalpha():
            variations.extend(
                [
                    f"NASDAQ:{search_term}",
                    f"NYSE:{search_term}",
                ]
            )

        return variations

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is supported by AKShare."""
        try:
            exchange, symbol = ticker.split(":", 1)

            # Exchange validation rules
            validation_rules = {
                "SSE": lambda s: s.isdigit() and len(s) == 6,
                "SZSE": lambda s: s.isdigit() and len(s) == 6,
                "BSE": lambda s: s.isdigit() and len(s) == 6,
                "HKEX": lambda s: s.isdigit() and 1 <= len(s) <= 5,
                "NASDAQ": lambda s: 1 <= len(s) <= 5,
                "NYSE": lambda s: 1 <= len(s) <= 5,
            }

            validator = validation_rules.get(exchange)
            return validator(symbol) if validator else False

        except ValueError:
            return False

    def get_market_calendar(
        self, start_date: datetime, end_date: datetime
    ) -> List[datetime]:
        """Get trading calendar for Chinese markets."""
        try:
            # Get trading calendar from AKShare
            df_calendar = ak.tool_trade_date_hist_sina()

            if df_calendar is None or df_calendar.empty:
                return []

            # Convert to datetime and filter by date range
            df_calendar["trade_date"] = pd.to_datetime(df_calendar["trade_date"])

            mask = (df_calendar["trade_date"] >= start_date) & (
                df_calendar["trade_date"] <= end_date
            )
            filtered_dates = df_calendar[mask]["trade_date"]

            return [date.to_pydatetime() for date in filtered_dates]

        except Exception as e:
            logger.error(f"Error fetching market calendar: {e}")
            return []

    def get_sector_stocks(self, sector: str) -> List[AssetSearchResult]:
        """Get stocks from a specific sector."""
        try:
            # Get sector classification
            df_industry = ak.stock_board_industry_name_em()

            if df_industry is None or df_industry.empty:
                return []

            # Find matching sectors
            sector_matches = df_industry[
                df_industry["板块名称"].str.contains(sector, na=False)
            ]

            results = []
            for _, sector_row in sector_matches.iterrows():
                try:
                    # Get stocks in this sector
                    sector_name = sector_row["板块名称"]
                    df_sector_stocks = ak.stock_board_industry_cons_em(
                        symbol=sector_name
                    )

                    if df_sector_stocks is not None and not df_sector_stocks.empty:
                        for _, stock_row in df_sector_stocks.iterrows():
                            stock_code = str(stock_row["代码"])
                            stock_name = stock_row["名称"]

                            # Determine exchange
                            exchange_info = self._get_exchange_from_a_share_code(
                                stock_code
                            )
                            if not exchange_info:
                                continue

                            exchange, internal_ticker = exchange_info

                            result = self._create_stock_search_result(
                                internal_ticker,
                                AssetType.STOCK,
                                stock_code,
                                stock_name,
                                exchange,
                                "CN",
                                "CNY",
                                "",
                            )
                            result.relevance_score = 1.0  # Override for sector search
                            results.append(result)

                except Exception as e:
                    logger.warning(
                        f"Error processing sector {sector_row.get('板块名称')}: {e}"
                    )
                    continue

            return results

        except Exception as e:
            logger.error(f"Error getting sector stocks for {sector}: {e}")
            return []

    def is_market_open(self, exchange: str) -> bool:
        """Check if market is currently open."""
        now = datetime.utcnow()

        # Market configurations: (timezone_offset, trading_sessions)
        market_config = {
            "SSE": (8, [("09:30", "11:30"), ("13:00", "15:00")]),
            "SZSE": (8, [("09:30", "11:30"), ("13:00", "15:00")]),
            "BSE": (8, [("09:30", "11:30"), ("13:00", "15:00")]),
            "HKEX": (8, [("09:30", "12:00"), ("13:00", "16:00")]),
            "NASDAQ": (-5, [("09:30", "16:00")]),
            "NYSE": (-5, [("09:30", "16:00")]),
            "CRYPTO": (0, [("00:00", "23:59")]),  # Always open
        }

        if exchange not in market_config:
            return False

        if exchange == "CRYPTO":
            return True

        timezone_offset, sessions = market_config[exchange]
        local_time = now.replace(tzinfo=None) + timedelta(hours=timezone_offset)

        # Check if it's a weekday
        if local_time.weekday() >= 5:
            return False

        current_time = local_time.time()

        # Check if current time falls within any trading session
        for start_str, end_str in sessions:
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            if start_time <= current_time <= end_time:
                return True

        return False
