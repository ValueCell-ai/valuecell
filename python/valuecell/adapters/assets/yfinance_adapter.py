"""Yahoo Finance adapter for asset data.

This adapter provides integration with Yahoo Finance API through the yfinance library
to fetch stock market data, including real-time prices and historical data.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

try:
    import yfinance as yf
except ImportError:
    yf = None

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


class YFinanceAdapter(BaseDataAdapter):
    """Yahoo Finance data adapter implementation."""

    def __init__(self, **kwargs):
        """Initialize Yahoo Finance adapter."""
        super().__init__(DataSource.YFINANCE, **kwargs)

        if yf is None:
            raise ImportError(
                "yfinance library is required. Install with: pip install yfinance"
            )

    def _initialize(self) -> None:
        """Initialize Yahoo Finance adapter configuration."""
        self.session = None  # yfinance handles sessions internally
        self.timeout = self.config.get("timeout", 30)

        # Asset type mapping for Yahoo Finance
        self.asset_type_mapping = {
            "EQUITY": AssetType.STOCK,
            "ETF": AssetType.ETF,
            "MUTUALFUND": AssetType.MUTUAL_FUND,
            "INDEX": AssetType.INDEX,
            "CURRENCY": AssetType.FOREX,
            "CRYPTOCURRENCY": AssetType.CRYPTO,
        }

        logger.info("Yahoo Finance adapter initialized")

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets using Yahoo Finance.

        Note: Yahoo Finance doesn't have a direct search API, so this implementation
        uses common ticker patterns and known symbols. For production use, consider
        integrating with a dedicated search service.
        """
        results = []
        search_term = query.query.upper().strip()

        # Try direct ticker lookup first
        try:
            ticker_obj = yf.Ticker(search_term)
            info = ticker_obj.info

            if info and "symbol" in info:
                result = self._create_search_result_from_info(info, query.language)
                if result:
                    results.append(result)
        except Exception as e:
            logger.debug(f"Direct ticker lookup failed for {search_term}: {e}")

        # Try with common suffixes for international markets
        if not results:
            suffixes = [".SS", ".SZ", ".HK", ".T", ".L", ".PA", ".DE"]
            for suffix in suffixes:
                try:
                    test_ticker = f"{search_term}{suffix}"
                    ticker_obj = yf.Ticker(test_ticker)
                    info = ticker_obj.info

                    if info and "symbol" in info:
                        result = self._create_search_result_from_info(
                            info, query.language
                        )
                        if result:
                            results.append(result)
                            break  # Found one, stop searching
                except Exception:
                    continue

        # Filter by asset types if specified
        if query.asset_types:
            results = [r for r in results if r.asset_type in query.asset_types]

        # Filter by exchanges if specified
        if query.exchanges:
            results = [r for r in results if r.exchange in query.exchanges]

        # Filter by countries if specified
        if query.countries:
            results = [r for r in results if r.country in query.countries]

        return results[: query.limit]

    def _create_search_result_from_info(
        self, info: Dict, language: str
    ) -> Optional[AssetSearchResult]:
        """Create search result from Yahoo Finance info dictionary."""
        try:
            symbol = info.get("symbol", "")
            if not symbol:
                return None

            # Convert to internal ticker format
            internal_ticker = self.convert_to_internal_ticker(symbol)

            # Get asset type
            asset_type = self.asset_type_mapping.get(
                info.get("quoteType", "").upper(), AssetType.STOCK
            )

            # Get exchange and country
            exchange = info.get("exchange", "UNKNOWN")
            country = info.get("country", "US")  # Default to US

            # Get names in different languages
            names = {
                "en-US": info.get("longName", info.get("shortName", symbol)),
            }

            # For Chinese markets, try to get Chinese name
            if exchange in ["SSE", "SHE"] and language.startswith("zh"):
                # This would require additional API calls or data sources
                # For now, use English name as fallback
                pass

            return AssetSearchResult(
                ticker=internal_ticker,
                asset_type=asset_type,
                names=names,
                exchange=exchange,
                country=country,
                currency=info.get("currency", "USD"),
                market_status=MarketStatus.UNKNOWN,  # Would need real-time data
                relevance_score=1.0,  # Simple relevance scoring
            )

        except Exception as e:
            logger.error(f"Error creating search result: {e}")
            return None

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed asset information from Yahoo Finance."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)
            ticker_obj = yf.Ticker(source_ticker)
            info = ticker_obj.info

            if not info or "symbol" not in info:
                return None

            # Create localized names
            names = LocalizedName()
            long_name = info.get("longName", info.get("shortName", ticker))
            names.set_name("en-US", long_name)

            # Create market info
            market_info = MarketInfo(
                exchange=info.get("exchange", "UNKNOWN"),
                country=info.get("country", "US"),
                currency=info.get("currency", "USD"),
                timezone=info.get("exchangeTimezoneName", "America/New_York"),
            )

            # Determine asset type
            asset_type = self.asset_type_mapping.get(
                info.get("quoteType", "").upper(), AssetType.STOCK
            )

            # Create asset object
            asset = Asset(
                ticker=ticker,
                asset_type=asset_type,
                names=names,
                market_info=market_info,
            )

            # Set source mapping
            asset.set_source_ticker(self.source, source_ticker)

            # Add additional properties
            properties = {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "website": info.get("website"),
                "business_summary": info.get("longBusinessSummary"),
            }

            # Filter out None values
            properties = {k: v for k, v in properties.items() if v is not None}
            asset.properties.update(properties)

            return asset

        except Exception as e:
            logger.error(f"Error fetching asset info for {ticker}: {e}")
            return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data from Yahoo Finance."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)
            ticker_obj = yf.Ticker(source_ticker)

            # Get current data
            data = ticker_obj.history(period="1d", interval="1m")
            if data.empty:
                return None

            # Get the most recent data point
            latest = data.iloc[-1]
            info = ticker_obj.info

            # Calculate change
            current_price = Decimal(str(latest["Close"]))
            previous_close = Decimal(str(info.get("previousClose", latest["Close"])))
            change = current_price - previous_close
            change_percent = (
                (change / previous_close) * 100 if previous_close else Decimal("0")
            )

            return AssetPrice(
                ticker=ticker,
                price=current_price,
                currency=info.get("currency", "USD"),
                timestamp=latest.name.to_pydatetime(),
                volume=Decimal(str(latest["Volume"])) if latest["Volume"] else None,
                open_price=Decimal(str(latest["Open"])),
                high_price=Decimal(str(latest["High"])),
                low_price=Decimal(str(latest["Low"])),
                close_price=current_price,
                change=change,
                change_percent=change_percent,
                market_cap=Decimal(str(info["marketCap"]))
                if info.get("marketCap")
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
        """Get historical price data from Yahoo Finance."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)
            ticker_obj = yf.Ticker(source_ticker)

            # Map interval to Yahoo Finance format
            interval_mapping = {
                "1m": "1m",
                "2m": "2m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "60m": "60m",
                "90m": "90m",
                "1h": "1h",
                "1d": "1d",
                "5d": "5d",
                "1w": "1wk",
                "1mo": "1mo",
                "3mo": "3mo",
            }
            yf_interval = interval_mapping.get(interval, "1d")

            # Fetch historical data
            data = ticker_obj.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=yf_interval,
            )

            if data.empty:
                return []

            # Get currency from ticker info
            info = ticker_obj.info
            currency = info.get("currency", "USD")

            prices = []
            for timestamp, row in data.iterrows():
                # Calculate change from previous day
                change = None
                change_percent = None

                if len(prices) > 0:
                    prev_close = prices[-1].close_price
                    change = Decimal(str(row["Close"])) - prev_close
                    change_percent = (
                        (change / prev_close) * 100 if prev_close else Decimal("0")
                    )

                price = AssetPrice(
                    ticker=ticker,
                    price=Decimal(str(row["Close"])),
                    currency=currency,
                    timestamp=timestamp.to_pydatetime(),
                    volume=Decimal(str(row["Volume"])) if row["Volume"] else None,
                    open_price=Decimal(str(row["Open"])),
                    high_price=Decimal(str(row["High"])),
                    low_price=Decimal(str(row["Low"])),
                    close_price=Decimal(str(row["Close"])),
                    change=change,
                    change_percent=change_percent,
                    source=self.source,
                )
                prices.append(price)

            return prices

        except Exception as e:
            logger.error(f"Error fetching historical prices for {ticker}: {e}")
            return []

    def get_multiple_prices(
        self, tickers: List[str]
    ) -> Dict[str, Optional[AssetPrice]]:
        """Get real-time prices for multiple assets efficiently."""
        try:
            # Convert to source tickers
            source_tickers = [self.convert_to_source_ticker(t) for t in tickers]

            # Use yfinance's download function for batch requests
            data = yf.download(
                source_tickers, period="1d", interval="1m", group_by="ticker"
            )

            results = {}

            for i, ticker in enumerate(tickers):
                try:
                    source_ticker = source_tickers[i]

                    if len(source_tickers) == 1:
                        # Single ticker case
                        ticker_data = data
                    else:
                        # Multiple tickers case
                        ticker_data = data[source_ticker]

                    if ticker_data.empty:
                        results[ticker] = None
                        continue

                    # Get the most recent data point
                    latest = ticker_data.iloc[-1]

                    # Get additional info for currency and market cap
                    ticker_obj = yf.Ticker(source_ticker)
                    info = ticker_obj.info

                    current_price = Decimal(str(latest["Close"]))
                    previous_close = Decimal(
                        str(info.get("previousClose", latest["Close"]))
                    )
                    change = current_price - previous_close
                    change_percent = (
                        (change / previous_close) * 100
                        if previous_close
                        else Decimal("0")
                    )

                    results[ticker] = AssetPrice(
                        ticker=ticker,
                        price=current_price,
                        currency=info.get("currency", "USD"),
                        timestamp=latest.name.to_pydatetime(),
                        volume=Decimal(str(latest["Volume"]))
                        if latest["Volume"]
                        else None,
                        open_price=Decimal(str(latest["Open"])),
                        high_price=Decimal(str(latest["High"])),
                        low_price=Decimal(str(latest["Low"])),
                        close_price=current_price,
                        change=change,
                        change_percent=change_percent,
                        market_cap=Decimal(str(info["marketCap"]))
                        if info.get("marketCap")
                        else None,
                        source=self.source,
                    )

                except Exception as e:
                    logger.error(f"Error processing ticker {ticker}: {e}")
                    results[ticker] = None

            return results

        except Exception as e:
            logger.error(f"Error fetching multiple prices: {e}")
            # Fallback to individual requests
            return super().get_multiple_prices(tickers)

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get asset types supported by Yahoo Finance."""
        return [
            AssetType.STOCK,
            AssetType.ETF,
            AssetType.MUTUAL_FUND,
            AssetType.INDEX,
            AssetType.FOREX,
            AssetType.CRYPTO,
            AssetType.OPTION,
            AssetType.FUTURE,
        ]

    def _perform_health_check(self) -> Any:
        """Perform health check by fetching a known ticker."""
        try:
            # Test with Apple stock
            ticker_obj = yf.Ticker("AAPL")
            info = ticker_obj.info

            if info and "symbol" in info:
                return {
                    "status": "ok",
                    "test_ticker": "AAPL",
                    "response_received": True,
                }
            else:
                return {"status": "error", "message": "No data received"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is supported by Yahoo Finance."""
        try:
            exchange, symbol = ticker.split(":", 1)

            # Yahoo Finance supports most major exchanges
            supported_exchanges = [
                "NASDAQ",
                "NYSE",
                "AMEX",  # US
                "SSE",
                "SZSE",  # China
                "HKEX",  # Hong Kong
                "TSE",  # Tokyo
                "LSE",  # London
                "EURONEXT",  # Europe
                "TSX",  # Toronto
                "ASX",  # Australia
            ]

            return exchange in supported_exchanges

        except ValueError:
            return False
