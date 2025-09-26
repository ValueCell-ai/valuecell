"""Finnhub adapter for global stock market data.

This adapter provides integration with Finnhub API to fetch global stock market data,
including US stocks, international markets, company profiles, and financial metrics.
"""

import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

from .base import (
    AuthenticationError,
    BaseDataAdapter,
    DataNotAvailableError,
    RateLimitError,
)
from .types import (
    Asset,
    AssetPrice,
    AssetSearchQuery,
    AssetSearchResult,
    AssetType,
    DataSource,
    LocalizedName,
    MarketInfo,
    MarketStatus,
)

logger = logging.getLogger(__name__)


class FinnhubAdapter(BaseDataAdapter):
    """Finnhub data adapter for global stock markets."""

    def __init__(self, api_key: str, **kwargs):
        """Initialize Finnhub adapter.

        Args:
            api_key: Finnhub API key
            **kwargs: Additional configuration parameters
        """
        super().__init__(DataSource.FINNHUB, api_key, **kwargs)

        if not api_key:
            raise AuthenticationError("Finnhub API key is required")

    def _initialize(self) -> None:
        """Initialize Finnhub adapter configuration."""
        self.base_url = "https://finnhub.io/api/v1"
        self.session = requests.Session()

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = (
            1.0  # Minimum 1 second between requests for free tier
        )

        # Asset type mapping for Finnhub
        self.asset_type_mapping = {
            "Common Stock": AssetType.STOCK,
            "ETF": AssetType.ETF,
            "Mutual Fund": AssetType.MUTUAL_FUND,
            "Index": AssetType.INDEX,
            "Bond": AssetType.BOND,
        }

        # Exchange mapping
        self.exchange_mapping = {
            "US": ["NASDAQ", "NYSE", "AMEX"],
            "HK": ["HKEX"],
            "CN": ["SSE", "SZSE"],
            "JP": ["TSE"],
            "GB": ["LSE"],
            "DE": ["XETRA"],
        }

        # Test connection
        try:
            self._perform_health_check()
            logger.info("Finnhub adapter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Finnhub adapter: {e}")
            raise AuthenticationError(f"Finnhub initialization failed: {e}")

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make rate-limited request to Finnhub API."""
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)

        url = f"{self.base_url}{endpoint}"
        request_params = params or {}
        request_params["token"] = self.api_key

        try:
            response = self.session.get(url, params=request_params, timeout=30)
            self.last_request_time = time.time()

            if response.status_code == 429:
                # Rate limit exceeded
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds",
                    retry_after=retry_after,
                    source=self.source,
                )
            elif response.status_code == 401:
                raise AuthenticationError("Invalid API key", source=self.source)
            elif response.status_code != 200:
                raise DataNotAvailableError(
                    f"API request failed with status {response.status_code}: {response.text}",
                    source=self.source,
                )

            data = response.json()

            # Check for API errors
            if isinstance(data, dict) and data.get("error"):
                raise DataNotAvailableError(
                    f"API error: {data['error']}", source=self.source
                )

            return data

        except requests.RequestException as e:
            raise DataNotAvailableError(f"Network error: {e}", source=self.source)

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets using Finnhub symbol lookup."""
        try:
            results = []
            search_term = query.query.upper().strip()

            # Search US stocks
            try:
                data = self._make_request("/search", {"q": search_term})

                if data and "result" in data:
                    for item in data["result"][: query.limit]:
                        try:
                            symbol = item.get("symbol", "")
                            description = item.get("description", "")
                            asset_type = item.get("type", "Common Stock")

                            if not symbol or not description:
                                continue

                            # Determine exchange and create internal ticker
                            exchange = self._determine_exchange(symbol)
                            internal_ticker = f"{exchange}:{symbol}"

                            # Map asset type
                            mapped_asset_type = self.asset_type_mapping.get(
                                asset_type, AssetType.STOCK
                            )

                            # Create localized names
                            names = {
                                "en-US": description,
                                "en-GB": description,
                                "zh-Hans": description,  # Could be enhanced with translation
                                "zh-Hant": description,
                            }

                            # Calculate relevance score
                            relevance_score = self._calculate_relevance(
                                search_term, symbol, description
                            )

                            result = AssetSearchResult(
                                ticker=internal_ticker,
                                asset_type=mapped_asset_type,
                                names=names,
                                exchange=exchange,
                                country=self._get_country_for_exchange(exchange),
                                currency=self._get_currency_for_exchange(exchange),
                                market_status=MarketStatus.UNKNOWN,
                                relevance_score=relevance_score,
                            )

                            results.append(result)

                        except Exception as e:
                            logger.warning(f"Error processing search result: {e}")
                            continue

            except Exception as e:
                logger.error(f"Error searching symbols: {e}")

            # Apply filters
            if query.asset_types:
                results = [r for r in results if r.asset_type in query.asset_types]

            if query.exchanges:
                results = [r for r in results if r.exchange in query.exchanges]

            if query.countries:
                results = [r for r in results if r.country in query.countries]

            # Sort by relevance
            results.sort(key=lambda x: x.relevance_score, reverse=True)

            return results[: query.limit]

        except Exception as e:
            logger.error(f"Error searching assets: {e}")
            return []

    def _calculate_relevance(
        self, search_term: str, symbol: str, description: str
    ) -> float:
        """Calculate relevance score for search results."""
        search_term_lower = search_term.lower()
        symbol_lower = symbol.lower()
        description_lower = description.lower()

        # Exact symbol match gets highest score
        if search_term_lower == symbol_lower:
            return 2.0

        # Symbol starts with search term
        if symbol_lower.startswith(search_term_lower):
            return 1.8

        # Description starts with search term
        if description_lower.startswith(search_term_lower):
            return 1.6

        # Symbol contains search term
        if search_term_lower in symbol_lower:
            return 1.4

        # Description contains search term
        if search_term_lower in description_lower:
            return 1.2

        return 1.0

    def _determine_exchange(self, symbol: str) -> str:
        """Determine exchange from symbol format."""
        # Simple heuristics for exchange determination
        if "." in symbol:
            suffix = symbol.split(".")[-1]
            if suffix == "HK":
                return "HKEX"
            elif suffix == "T":
                return "TSE"
            elif suffix == "L":
                return "LSE"
            elif suffix == "DE":
                return "XETRA"

        # Default to NASDAQ for US symbols
        return "NASDAQ"

    def _get_country_for_exchange(self, exchange: str) -> str:
        """Get country code for exchange."""
        country_mapping = {
            "NASDAQ": "US",
            "NYSE": "US",
            "AMEX": "US",
            "HKEX": "HK",
            "TSE": "JP",
            "LSE": "GB",
            "XETRA": "DE",
            "SSE": "CN",
            "SZSE": "CN",
        }
        return country_mapping.get(exchange, "US")

    def _get_currency_for_exchange(self, exchange: str) -> str:
        """Get currency for exchange."""
        currency_mapping = {
            "NASDAQ": "USD",
            "NYSE": "USD",
            "AMEX": "USD",
            "HKEX": "HKD",
            "TSE": "JPY",
            "LSE": "GBP",
            "XETRA": "EUR",
            "SSE": "CNY",
            "SZSE": "CNY",
        }
        return currency_mapping.get(exchange, "USD")

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed asset information from Finnhub."""
        try:
            exchange, symbol = ticker.split(":")

            # Get company profile
            try:
                profile_data = self._make_request("/stock/profile2", {"symbol": symbol})

                if not profile_data:
                    return None

                # Create localized names
                names = LocalizedName()
                company_name = profile_data.get("name", symbol)
                names.set_name("en-US", company_name)
                names.set_name("en-GB", company_name)
                names.set_name("zh-Hans", company_name)  # Could be enhanced
                names.set_name("zh-Hant", company_name)

                # Create market info
                country = profile_data.get(
                    "country", self._get_country_for_exchange(exchange)
                )
                currency = profile_data.get(
                    "currency", self._get_currency_for_exchange(exchange)
                )

                market_info = MarketInfo(
                    exchange=exchange,
                    country=country,
                    currency=currency,
                    timezone=self._get_timezone_for_country(country),
                )

                # Create asset
                asset = Asset(
                    ticker=ticker,
                    asset_type=AssetType.STOCK,  # Default to stock, could be enhanced
                    names=names,
                    market_info=market_info,
                )

                # Set source mapping
                asset.set_source_ticker(self.source, symbol)

                # Add additional properties
                properties = {
                    "country": profile_data.get("country"),
                    "currency": profile_data.get("currency"),
                    "exchange": profile_data.get("exchange"),
                    "ipo": profile_data.get("ipo"),
                    "market_capitalization": profile_data.get("marketCapitalization"),
                    "outstanding_shares": profile_data.get("shareOutstanding"),
                    "name": profile_data.get("name"),
                    "phone": profile_data.get("phone"),
                    "weburl": profile_data.get("weburl"),
                    "logo": profile_data.get("logo"),
                    "finnhub_industry": profile_data.get("finnhubIndustry"),
                }

                # Filter out None values
                properties = {k: v for k, v in properties.items() if v is not None}
                asset.properties.update(properties)

                return asset

            except Exception as e:
                logger.error(f"Error fetching company profile for {symbol}: {e}")
                return None

        except Exception as e:
            logger.error(f"Error getting asset info for {ticker}: {e}")
            return None

    def _get_timezone_for_country(self, country: str) -> str:
        """Get timezone for country."""
        timezone_mapping = {
            "US": "America/New_York",
            "HK": "Asia/Hong_Kong",
            "JP": "Asia/Tokyo",
            "GB": "Europe/London",
            "DE": "Europe/Berlin",
            "CN": "Asia/Shanghai",
        }
        return timezone_mapping.get(country, "America/New_York")

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data from Finnhub."""
        try:
            exchange, symbol = ticker.split(":")

            # Get real-time quote
            try:
                quote_data = self._make_request("/quote", {"symbol": symbol})

                if not quote_data or "c" not in quote_data:
                    return None

                current_price = Decimal(str(quote_data["c"]))  # Current price
                open_price = Decimal(str(quote_data["o"]))  # Open price
                high_price = Decimal(str(quote_data["h"]))  # High price
                low_price = Decimal(str(quote_data["l"]))  # Low price
                previous_close = Decimal(str(quote_data["pc"]))  # Previous close

                # Calculate change
                change = current_price - previous_close
                change_percent = (
                    (change / previous_close) * 100 if previous_close else Decimal("0")
                )

                # Timestamp (Unix timestamp)
                timestamp = (
                    datetime.fromtimestamp(quote_data["t"])
                    if quote_data.get("t")
                    else datetime.now()
                )

                return AssetPrice(
                    ticker=ticker,
                    price=current_price,
                    currency=self._get_currency_for_exchange(exchange),
                    timestamp=timestamp,
                    volume=None,  # Volume not provided in basic quote
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=current_price,
                    change=change,
                    change_percent=change_percent,
                    source=self.source,
                )

            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")
                return None

        except Exception as e:
            logger.error(f"Error getting real-time price for {ticker}: {e}")
            return None

    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[AssetPrice]:
        """Get historical price data from Finnhub."""
        try:
            exchange, symbol = ticker.split(":")

            # Convert dates to Unix timestamps
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())

            # Map interval to Finnhub resolution
            resolution_mapping = {
                "1m": "1",
                "5m": "5",
                "15m": "15",
                "30m": "30",
                "1h": "60",
                "1d": "D",
                "daily": "D",
                "1w": "W",
                "1mo": "M",
            }

            resolution = resolution_mapping.get(interval, "D")

            try:
                # Get historical data (candles)
                candle_data = self._make_request(
                    "/stock/candle",
                    {
                        "symbol": symbol,
                        "resolution": resolution,
                        "from": start_timestamp,
                        "to": end_timestamp,
                    },
                )

                if not candle_data or candle_data.get("s") != "ok":
                    return []

                # Extract data arrays
                timestamps = candle_data.get("t", [])
                opens = candle_data.get("o", [])
                highs = candle_data.get("h", [])
                lows = candle_data.get("l", [])
                closes = candle_data.get("c", [])
                volumes = candle_data.get("v", [])

                if not all([timestamps, opens, highs, lows, closes]):
                    return []

                prices = []
                currency = self._get_currency_for_exchange(exchange)

                for i in range(len(timestamps)):
                    # Convert timestamp
                    trade_date = datetime.fromtimestamp(timestamps[i])

                    # Extract price data
                    open_price = Decimal(str(opens[i]))
                    high_price = Decimal(str(highs[i]))
                    low_price = Decimal(str(lows[i]))
                    close_price = Decimal(str(closes[i]))
                    volume = (
                        Decimal(str(volumes[i]))
                        if i < len(volumes) and volumes[i]
                        else None
                    )

                    # Calculate change from previous day
                    change = None
                    change_percent = None
                    if i > 0:
                        prev_close = Decimal(str(closes[i - 1]))
                        change = close_price - prev_close
                        change_percent = (
                            (change / prev_close) * 100 if prev_close else Decimal("0")
                        )

                    price = AssetPrice(
                        ticker=ticker,
                        price=close_price,
                        currency=currency,
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

                return prices

            except Exception as e:
                logger.error(f"Error fetching historical data for {symbol}: {e}")
                return []

        except Exception as e:
            logger.error(f"Error getting historical prices for {ticker}: {e}")
            return []

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get asset types supported by Finnhub."""
        return [
            AssetType.STOCK,
            AssetType.ETF,
            AssetType.MUTUAL_FUND,
            AssetType.INDEX,
        ]

    def _perform_health_check(self) -> Any:
        """Perform health check by fetching API status."""
        try:
            # Test with a simple quote request for AAPL
            data = self._make_request("/quote", {"symbol": "AAPL"})

            if data and "c" in data:
                return {
                    "status": "ok",
                    "test_symbol": "AAPL",
                    "current_price": data["c"],
                }
            else:
                return {"status": "error", "message": "No data received"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is supported by Finnhub."""
        try:
            exchange, symbol = ticker.split(":", 1)

            # Finnhub supports major global exchanges
            supported_exchanges = [
                "NASDAQ",
                "NYSE",
                "AMEX",  # US
                "HKEX",  # Hong Kong
                "TSE",  # Tokyo
                "LSE",  # London
                "XETRA",  # Germany
            ]

            return exchange in supported_exchanges

        except ValueError:
            return False

    def get_company_news(
        self, ticker: str, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get company news from Finnhub."""
        try:
            exchange, symbol = ticker.split(":")

            # Convert dates to YYYY-MM-DD format
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            news_data = self._make_request(
                "/company-news",
                {"symbol": symbol, "from": start_date_str, "to": end_date_str},
            )

            if not news_data:
                return []

            news_items = []
            for item in news_data:
                news_item = {
                    "id": item.get("id"),
                    "category": item.get("category"),
                    "datetime": datetime.fromtimestamp(item.get("datetime", 0)),
                    "headline": item.get("headline"),
                    "image": item.get("image"),
                    "related": item.get("related"),
                    "source": item.get("source"),
                    "summary": item.get("summary"),
                    "url": item.get("url"),
                }
                news_items.append(news_item)

            return news_items

        except Exception as e:
            logger.error(f"Error fetching company news for {ticker}: {e}")
            return []

    def get_basic_financials(self, ticker: str) -> Dict[str, Any]:
        """Get basic financial metrics from Finnhub."""
        try:
            exchange, symbol = ticker.split(":")

            financials_data = self._make_request(
                "/stock/metric", {"symbol": symbol, "metric": "all"}
            )

            if not financials_data:
                return {}

            # Extract key metrics
            metrics = financials_data.get("metric", {})

            return {
                "market_cap": metrics.get("marketCapitalization"),
                "pe_ratio": metrics.get("peBasicExclExtraTTM"),
                "pb_ratio": metrics.get("pbQuarterly"),
                "dividend_yield": metrics.get("dividendYieldIndicatedAnnual"),
                "beta": metrics.get("beta"),
                "eps_ttm": metrics.get("epsBasicExclExtraItemsTTM"),
                "revenue_ttm": metrics.get("revenueTTM"),
                "gross_margin": metrics.get("grossMarginTTM"),
                "operating_margin": metrics.get("operatingMarginTTM"),
                "net_margin": metrics.get("netProfitMarginTTM"),
                "roe": metrics.get("roeTTM"),
                "roa": metrics.get("roaTTM"),
                "debt_to_equity": metrics.get("totalDebt/totalEquityQuarterly"),
                "52_week_high": metrics.get("52WeekHigh"),
                "52_week_low": metrics.get("52WeekLow"),
            }

        except Exception as e:
            logger.error(f"Error fetching basic financials for {ticker}: {e}")
            return {}

    def is_market_open(self, exchange: str) -> bool:
        """Check if a specific market is currently open."""
        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday()

        # Skip weekends
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Basic market hours (approximate)
        if exchange in ["NASDAQ", "NYSE", "AMEX"]:
            # US market hours: 9:30 AM - 4:00 PM EST = 14:30 - 21:00 UTC
            return 14 <= hour < 21
        elif exchange == "HKEX":
            # Hong Kong: 9:30 AM - 4:00 PM HKT = 1:30 - 8:00 UTC
            return 1 <= hour < 8
        elif exchange == "TSE":
            # Tokyo: 9:00 AM - 3:00 PM JST = 0:00 - 6:00 UTC
            return 0 <= hour < 6
        elif exchange == "LSE":
            # London: 8:00 AM - 4:30 PM GMT = 8:00 - 16:30 UTC
            return 8 <= hour < 17
        elif exchange == "XETRA":
            # Germany: 9:00 AM - 5:30 PM CET = 8:00 - 16:30 UTC
            return 8 <= hour < 17

        return False
