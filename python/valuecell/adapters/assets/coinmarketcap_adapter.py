"""CoinMarketCap adapter for cryptocurrency data.

This adapter provides integration with CoinMarketCap API to fetch cryptocurrency
market data, including prices, market caps, and metadata.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
import requests
import time

from .base import (
    BaseDataAdapter,
    DataNotAvailableError,
    AuthenticationError,
    RateLimitError,
)
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


class CoinMarketCapAdapter(BaseDataAdapter):
    """CoinMarketCap data adapter for cryptocurrency markets."""

    def __init__(self, api_key: str, **kwargs):
        """Initialize CoinMarketCap adapter.

        Args:
            api_key: CoinMarketCap API key
            **kwargs: Additional configuration parameters
        """
        super().__init__(DataSource.COINMARKETCAP, api_key, **kwargs)

        if not api_key:
            raise AuthenticationError("CoinMarketCap API key is required")

    def _initialize(self) -> None:
        """Initialize CoinMarketCap adapter configuration."""
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": self.api_key,
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests

        # Test connection
        try:
            self._perform_health_check()
            logger.info("CoinMarketCap adapter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CoinMarketCap adapter: {e}")
            raise AuthenticationError(f"CoinMarketCap initialization failed: {e}")

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make rate-limited request to CoinMarketCap API."""
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(url, params=params or {})
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
            if data.get("status", {}).get("error_code") != 0:
                error_message = data.get("status", {}).get(
                    "error_message", "Unknown error"
                )
                raise DataNotAvailableError(
                    f"API error: {error_message}", source=self.source
                )

            return data

        except requests.RequestException as e:
            raise DataNotAvailableError(f"Network error: {e}", source=self.source)

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for cryptocurrencies using CoinMarketCap."""
        try:
            # CoinMarketCap doesn't have a direct search endpoint in free tier
            # We'll get the top cryptocurrencies and filter by name/symbol
            params = {
                "start": 1,
                "limit": 5000,  # Get more coins to search through
                "convert": "USD",
            }

            data = self._make_request("/cryptocurrency/listings/latest", params)
            coins = data.get("data", [])

            search_term = query.query.lower().strip()
            results = []

            for coin in coins:
                # Search by symbol or name
                symbol = coin.get("symbol", "").lower()
                name = coin.get("name", "").lower()

                if (
                    search_term in symbol
                    or search_term in name
                    or symbol.startswith(search_term)
                ):
                    # Convert to internal ticker format
                    internal_ticker = f"CRYPTO:{coin['symbol']}"

                    # Create localized names
                    names = {
                        "en-US": coin["name"],
                        "zh-Hans": coin["name"],  # Could be enhanced with translations
                    }

                    # Calculate relevance score
                    relevance_score = 1.0
                    if symbol == search_term:
                        relevance_score = 2.0  # Exact symbol match
                    elif symbol.startswith(search_term):
                        relevance_score = 1.5  # Symbol starts with search term

                    result = AssetSearchResult(
                        ticker=internal_ticker,
                        asset_type=AssetType.CRYPTO,
                        names=names,
                        exchange="CRYPTO",
                        country="GLOBAL",
                        currency="USD",
                        market_status=MarketStatus.OPEN,  # Crypto markets are always open
                        relevance_score=relevance_score,
                    )

                    results.append(result)

            # Sort by relevance score and market cap
            results.sort(key=lambda x: (x.relevance_score, -1), reverse=True)

            # Apply filters
            if query.asset_types:
                results = [r for r in results if r.asset_type in query.asset_types]

            return results[: query.limit]

        except Exception as e:
            logger.error(f"Error searching cryptocurrencies: {e}")
            return []

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed cryptocurrency information from CoinMarketCap."""
        try:
            # Extract symbol from ticker
            symbol = self.get_symbol()

            # Get cryptocurrency metadata
            params = {"symbol": symbol}
            data = self._make_request("/cryptocurrency/info", params)

            coin_data = data.get("data", {}).get(symbol)
            if not coin_data:
                return None

            # Create localized names
            names = LocalizedName()
            names.set_name("en-US", coin_data["name"])
            names.set_name("zh-Hans", coin_data["name"])  # Could be enhanced

            # Create market info
            market_info = MarketInfo(
                exchange="CRYPTO", country="GLOBAL", currency="USD", timezone="UTC"
            )

            # Create asset
            asset = Asset(
                ticker=ticker,
                asset_type=AssetType.CRYPTO,
                names=names,
                market_info=market_info,
            )

            # Set source mapping
            asset.set_source_ticker(self.source, symbol)

            # Add additional properties
            properties = {
                "description": coin_data.get("description"),
                "category": coin_data.get("category"),
                "tags": coin_data.get("tags", []),
                "platform": coin_data.get("platform"),
                "date_added": coin_data.get("date_added"),
                "date_launched": coin_data.get("date_launched"),
                "is_hidden": coin_data.get("is_hidden"),
                "notice": coin_data.get("notice"),
                "logo": coin_data.get("logo"),
                "subreddit": coin_data.get("subreddit"),
                "twitter_username": coin_data.get("twitter_username"),
                "website_url": coin_data.get("urls", {}).get("website", []),
                "technical_doc": coin_data.get("urls", {}).get("technical_doc", []),
                "explorer": coin_data.get("urls", {}).get("explorer", []),
                "source_code": coin_data.get("urls", {}).get("source_code", []),
            }

            # Filter out None values
            properties = {k: v for k, v in properties.items() if v is not None}
            asset.properties.update(properties)

            return asset

        except Exception as e:
            logger.error(f"Error fetching asset info for {ticker}: {e}")
            return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time cryptocurrency price from CoinMarketCap."""
        try:
            symbol = self.get_symbol(ticker)

            params = {"symbol": symbol, "convert": "USD"}

            data = self._make_request("/cryptocurrency/quotes/latest", params)
            coin_data = data.get("data", {}).get(symbol)

            if not coin_data:
                return None

            quote = coin_data["quote"]["USD"]

            # Convert timestamp
            last_updated = datetime.fromisoformat(
                coin_data["last_updated"].replace("Z", "+00:00")
            ).replace(tzinfo=None)

            return AssetPrice(
                ticker=ticker,
                price=Decimal(str(quote["price"])),
                currency="USD",
                timestamp=last_updated,
                volume=Decimal(str(quote["volume_24h"]))
                if quote.get("volume_24h")
                else None,
                change=None,  # CoinMarketCap doesn't provide absolute change
                change_percent=Decimal(str(quote["percent_change_24h"]))
                if quote.get("percent_change_24h")
                else None,
                market_cap=Decimal(str(quote["market_cap"]))
                if quote.get("market_cap")
                else None,
                source=self.source,
            )

        except Exception as e:
            logger.error(f"Error fetching real-time price for {ticker}: {e}")
            return None

    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[AssetPrice]:
        """Get historical cryptocurrency prices from CoinMarketCap.

        Note: Historical data requires a paid CoinMarketCap plan.
        This implementation provides a placeholder structure.
        """
        try:
            # CoinMarketCap historical data requires paid plan
            # This is a placeholder implementation
            logger.warning(
                f"Historical data for {ticker} requires CoinMarketCap paid plan. "
                f"Consider using alternative data sources for historical crypto data."
            )

            return []

        except Exception as e:
            logger.error(f"Error fetching historical prices for {ticker}: {e}")
            return []

    def get_multiple_prices(
        self, tickers: List[str]
    ) -> Dict[str, Optional[AssetPrice]]:
        """Get real-time prices for multiple cryptocurrencies efficiently."""
        try:
            # Extract symbols from tickers
            symbols = [self.get_symbol(ticker) for ticker in tickers]

            # CoinMarketCap supports comma-separated symbols
            params = {"symbol": ",".join(symbols), "convert": "USD"}

            data = self._make_request("/cryptocurrency/quotes/latest", params)
            coin_data = data.get("data", {})

            results = {}

            for ticker in tickers:
                symbol = self.get_symbol(ticker)

                if symbol in coin_data:
                    coin_info = coin_data[symbol]
                    quote = coin_info["quote"]["USD"]

                    last_updated = datetime.fromisoformat(
                        coin_info["last_updated"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)

                    results[ticker] = AssetPrice(
                        ticker=ticker,
                        price=Decimal(str(quote["price"])),
                        currency="USD",
                        timestamp=last_updated,
                        volume=Decimal(str(quote["volume_24h"]))
                        if quote.get("volume_24h")
                        else None,
                        change=None,
                        change_percent=Decimal(str(quote["percent_change_24h"]))
                        if quote.get("percent_change_24h")
                        else None,
                        market_cap=Decimal(str(quote["market_cap"]))
                        if quote.get("market_cap")
                        else None,
                        source=self.source,
                    )
                else:
                    results[ticker] = None

            return results

        except Exception as e:
            logger.error(f"Error fetching multiple prices: {e}")
            # Fallback to individual requests
            return super().get_multiple_prices(tickers)

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get asset types supported by CoinMarketCap."""
        return [AssetType.CRYPTO]

    def _perform_health_check(self) -> Any:
        """Perform health check by fetching API info."""
        try:
            data = self._make_request("/key/info")

            if "data" in data:
                return {
                    "status": "ok",
                    "plan": data["data"].get("plan", {}).get("name"),
                    "credits_left": data["data"]
                    .get("usage", {})
                    .get("current_month", {})
                    .get("credits_left"),
                    "credits_used": data["data"]
                    .get("usage", {})
                    .get("current_month", {})
                    .get("credits_used"),
                }
            else:
                return {"status": "error", "message": "No data received"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is a cryptocurrency ticker."""
        try:
            exchange, symbol = ticker.split(":", 1)

            # CoinMarketCap supports crypto tickers
            supported_exchanges = ["CRYPTO"]

            return exchange in supported_exchanges

        except ValueError:
            return False

    def get_symbol(self, ticker: str) -> str:
        """Extract symbol from internal ticker format."""
        try:
            return ticker.split(":", 1)[1]
        except (ValueError, IndexError):
            return ticker

    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global cryptocurrency market metrics."""
        try:
            data = self._make_request("/global-metrics/quotes/latest")
            return data.get("data", {})

        except Exception as e:
            logger.error(f"Error fetching global metrics: {e}")
            return {}

    def get_trending_cryptocurrencies(self, limit: int = 10) -> List[AssetSearchResult]:
        """Get trending cryptocurrencies by market cap."""
        try:
            params = {
                "start": 1,
                "limit": limit,
                "convert": "USD",
                "sort": "market_cap",
                "sort_dir": "desc",
            }

            data = self._make_request("/cryptocurrency/listings/latest", params)
            coins = data.get("data", [])

            results = []
            for coin in coins:
                internal_ticker = f"CRYPTO:{coin['symbol']}"

                names = {
                    "en-US": coin["name"],
                    "zh-Hans": coin["name"],
                }

                result = AssetSearchResult(
                    ticker=internal_ticker,
                    asset_type=AssetType.CRYPTO,
                    names=names,
                    exchange="CRYPTO",
                    country="GLOBAL",
                    currency="USD",
                    market_status=MarketStatus.OPEN,
                    relevance_score=1.0,
                )

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error fetching trending cryptocurrencies: {e}")
            return []

    def is_market_open(self, exchange: str) -> bool:
        """Cryptocurrency markets are always open."""
        if exchange in ["CRYPTO"]:
            return True
        return False
